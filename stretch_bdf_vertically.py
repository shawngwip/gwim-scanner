import math

def safe_stretch_bdf_vertical(input_path, output_path, scale=2):
    with open(input_path, "r") as f:
        lines = f.readlines()

    out = []
    inside_char = False
    bitmap = []
    new_bitmap = []
    bbx_line_index = None

    for i, line in enumerate(lines):
        if line.startswith("STARTCHAR"):
            inside_char = True
            char_lines = [line]
            bitmap = []
            new_bitmap = []
            bbx_line_index = None
        elif inside_char:
            char_lines.append(line)
            if line.startswith("BBX "):
                bbx_line_index = len(char_lines) - 1
                parts = line.strip().split()
                width, height, x_offset, y_offset = map(int, parts[1:])
            elif line.strip() == "BITMAP":
                bitmap = []
            elif line.strip() == "ENDCHAR":
                # Stretch only if BBX line found and bitmap collected
                if bbx_line_index is not None:
                    stretched = []
                    for hexline in bitmap:
                        stretched.extend([hexline] * scale)

                    # Modify BBX height
                    new_height = len(stretched)
                    old_bbx_line = char_lines[bbx_line_index]
                    parts = old_bbx_line.strip().split()
                    new_bbx_line = f"BBX {parts[1]} {new_height} {parts[3]} {parts[4]}\n"
                    char_lines[bbx_line_index] = new_bbx_line

                    # Rebuild char_lines with updated BITMAP
                    out.extend(char_lines[:-len(bitmap)-1])  # Before BITMAP
                    out.append("BITMAP\n")
                    out.extend(stretched)
                    out.append("ENDCHAR\n")
                else:
                    out.extend(char_lines)
                inside_char = False
            elif all(c in "0123456789ABCDEFabcdef" for c in line.strip()):
                bitmap.append(line)
        else:
            out.append(line)

    with open(output_path, "w") as f:
        f.writelines(out)
    print(f"Saved: {output_path}")

def safe_stretch_bdf_vertical_point(input_path, output_path, scale=1.5):
    with open(input_path, "r") as f:
        lines = f.readlines()

    out = []
    inside_char = False
    bitmap = []
    bbx_line_index = None

    for i, line in enumerate(lines):
        if line.startswith("STARTCHAR"):
            inside_char = True
            char_lines = [line]
            bitmap = []
            bbx_line_index = None
        elif inside_char:
            char_lines.append(line)
            if line.startswith("BBX "):
                bbx_line_index = len(char_lines) - 1
                parts = line.strip().split()
                width, height, x_offset, y_offset = map(int, parts[1:])
            elif line.strip() == "BITMAP":
                bitmap = []
            elif line.strip() == "ENDCHAR":
                if bbx_line_index is not None:
                    # Simulate vertical scaling using floating-point accumulation
                    stretched = []
                    current_y = 0.0
                    for hexline in bitmap:
                        next_y = current_y + scale
                        lines_to_add = int(next_y) - int(current_y)
                        for _ in range(lines_to_add):
                            cleaned = hexline.strip().upper()
                            if cleaned != "":
                                stretched.append(f"{cleaned}\n")
                        current_y = next_y

                    # Update BBX height
                    parts = char_lines[bbx_line_index].strip().split()
                    parts[2] = str(len(stretched))  # height
                    char_lines[bbx_line_index] = " ".join(parts) + "\n"

                    # Write everything before BITMAP
                    out.extend(char_lines[:-len(bitmap)-1])
                    out.append("BITMAP\n")
                    out.extend(stretched)
                    out.append("ENDCHAR\n")
                else:
                    out.extend(char_lines)
                    out.append("ENDCHAR\n")
                inside_char = False
            elif all(c in "0123456789ABCDEFabcdef" for c in line.strip()):
                bitmap.append(line)
        else:
            out.append(line)

    with open(output_path, "w") as f:
        f.writelines(out)

    print(f"Saved stretched font to: {output_path}")



def safe_stretch_bdf_horizontal(input_path, output_path, scale=2):
    def stretch_hex_line(hex_line, scale, width):
        # Convert to binary string, pad to full width
        bin_line = bin(int(hex_line, 16))[2:].zfill(width)
        # Stretch horizontally by repeating each bit
        stretched_bits = ''.join(bit * scale for bit in bin_line)
        # Pad to next byte (8-bit) boundary
        padded_len = ((len(stretched_bits) + 7) // 8) * 8
        stretched_bits = stretched_bits.ljust(padded_len, '0')
        # Convert back to hex
        hex_out = ''
        for i in range(0, padded_len, 8):
            hex_out += f"{int(stretched_bits[i:i+8], 2):02X}"
        return hex_out

    with open(input_path, "r") as f:
        lines = f.readlines()

    out = []
    inside_char = False
    bitmap = []
    new_bitmap = []
    bbx_line_index = None

    for i, line in enumerate(lines):
        if line.startswith("STARTCHAR"):
            inside_char = True
            char_lines = [line]
            bitmap = []
            new_bitmap = []
            bbx_line_index = None
        elif inside_char:
            char_lines.append(line)
            if line.startswith("BBX "):
                bbx_line_index = len(char_lines) - 1
                parts = line.strip().split()
                width, height, x_offset, y_offset = map(int, parts[1:])
            elif line.strip() == "BITMAP":
                bitmap = []
            elif line.strip() == "ENDCHAR":
                if bbx_line_index is not None:
                    stretched = []
                    for hexline in bitmap:
                        stretched_line = stretch_hex_line(hexline.strip(), scale, width)
                        stretched.append(stretched_line)

                    # Modify BBX width
                    new_width = width * scale
                    parts = char_lines[bbx_line_index].strip().split()
                    parts[1] = str(new_width)
                    new_bbx_line = " ".join(parts) + "\n"
                    char_lines[bbx_line_index] = new_bbx_line

                    # Modify DWIDTH line if present
                    for idx, l in enumerate(char_lines):
                        if l.startswith("DWIDTH "):
                            dw_parts = l.strip().split()
                            dw_parts[1] = str(int(dw_parts[1]) * scale)
                            char_lines[idx] = " ".join(dw_parts) + "\n"

                    # Rebuild char_lines with new stretched bitmap
                    out.extend(char_lines[:-len(bitmap)-1])  # before BITMAP
                    out.append("BITMAP\n")
                    out.extend(line + "\n" for line in stretched)
                    out.append("ENDCHAR\n")
                else:
                    out.extend(char_lines)
                    out.append("ENDCHAR\n")
                inside_char = False
            elif all(c in "0123456789ABCDEFabcdef" for c in line.strip()):
                bitmap.append(line.strip())
        else:
            out.append(line)

    with open(output_path, "w") as f:
        f.writelines(out)
    print(f"Saved: {output_path}")

def add_horizontal_gap_to_bdf(input_file, output_file):
    with open(input_file, "r") as f:
        lines = f.readlines()

    output_lines = []
    inside_char = False
    bitmap_lines = []
    bbx_index = None
    dwidth_index = None

    for i, line in enumerate(lines):
        if line.startswith("STARTCHAR"):
            inside_char = True
            char_block = [line]
            bitmap_lines = []
            bbx_index = None
            dwidth_index = None
        elif inside_char:
            if line.startswith("BBX "):
                bbx_index = len(char_block)
            if line.startswith("DWIDTH "):
                dwidth_index = len(char_block)
            if line.strip() == "BITMAP":
                char_block.append(line)
                bitmap_lines = []
            elif line.strip() == "ENDCHAR":
                # Modify bitmap
                new_bitmap_lines = []
                for hex_line in bitmap_lines:
                    b = bin(int(hex_line.strip(), 16))[2:].zfill(8)  # assume 8-bit width
                    new_b = ""
                    for bit in b:
                        new_b += bit + "0"  # add a 0 (gap) after each bit
                    padded = new_b.ljust(16, "0")
                    new_hex = hex(int(padded, 2))[2:].zfill(4).upper()
                    new_bitmap_lines.append(new_hex)

                # Update BBX and DWIDTH
                if bbx_index is not None:
                    parts = char_block[bbx_index].split()
                    new_width = int(parts[1]) * 2  # double width
                    parts[1] = str(new_width)
                    char_block[bbx_index] = " ".join(parts) + "\n"

                if dwidth_index is not None:
                    parts = char_block[dwidth_index].split()
                    new_dwidth = int(parts[1]) * 2
                    parts[1] = str(new_dwidth)
                    char_block[dwidth_index] = " ".join(parts) + "\n"

                # Append new bitmap and end
                for line in new_bitmap_lines:
                    char_block.append(line + "\n")
                char_block.append("ENDCHAR\n")
                output_lines.extend(char_block)
                inside_char = False
            elif line.strip() != "BITMAP":
                char_block.append(line)
            else:
                bitmap_lines.append(line)
        else:
            output_lines.append(line)

    with open(output_file, "w") as f:
        f.writelines(output_lines)
    print(f"Done. Output written to: {output_file}")

def reduce_dot_width_in_bdf(input_file, output_file, new_width=3):
    with open(input_file, "r") as f:
        lines = f.readlines()

    output_lines = []
    inside_dot = False
    bitmap_started = False
    bitmap_lines = []
    modified = False

    for i, line in enumerate(lines):
        if line.startswith("STARTCHAR .") or line.startswith("ENCODING 46"):
            inside_dot = True
            char_block = [line]
            bitmap_lines = []
            continue

        if inside_dot:
            char_block.append(line)

            if line.startswith("BBX "):
                parts = line.split()
                old_width = int(parts[1])
                height = int(parts[2])
                x_offset = int(parts[3])
                y_offset = int(parts[4])

                # Update BBX width
                parts[1] = str(new_width)
                new_bbx_line = " ".join(parts) + "\n"
                char_block[-1] = new_bbx_line

            elif line.startswith("DWIDTH "):
                parts = line.split()
                parts[1] = str(new_width)
                char_block[-1] = " ".join(parts) + "\n"

            elif line.strip() == "BITMAP":
                bitmap_started = True
                bitmap_lines = []
            elif bitmap_started and not line.strip() == "ENDCHAR":
                bitmap_lines.append(line.strip())
            elif line.strip() == "ENDCHAR":
                # Trim each bitmap line to only use new_width bits (left-aligned)
                new_bitmap = []
                for hex_line in bitmap_lines:
                    b = bin(int(hex_line, 16))[2:].zfill(8)  # assume max 8 bits
                    new_b = b[:new_width].ljust(8, "0")
                    new_hex = hex(int(new_b, 2))[2:].zfill(2).upper()
                    new_bitmap.append(new_hex + "\n")

                char_block = char_block[:-len(bitmap_lines)-1]  # remove old BITMAP + lines
                char_block.append("BITMAP\n")
                char_block.extend(new_bitmap)
                char_block.append("ENDCHAR\n")
                output_lines.extend(char_block)

                inside_dot = False
                bitmap_started = False
                modified = True
        else:
            output_lines.append(line)

    with open(output_file, "w") as f:
        f.writelines(output_lines)

    if modified:
        print(f"Dot character width reduced to {new_width} and saved to {output_file}")
    else:
        print("Dot character not found or unchanged.")

safe_stretch_bdf_vertical_point("helvB12.bdf", "helvB12-vp.bdf", scale=1.5)
