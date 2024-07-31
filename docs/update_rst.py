import os

def update_rst_files(directory, prefix):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.rst'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.readlines()

                with open(file_path, 'w') as f:
                    for line in content:
                        if line.startswith(".. automodule:: "):
                            line = line.replace(".. automodule:: ", f".. automodule:: {prefix}")
                        f.write(line)

if __name__ == "__main__":
    rst_directory = "./docs/source"
    module_prefix = "districtheatsim."

    update_rst_files(rst_directory, module_prefix)
    print("Die rst-Dateien wurden erfolgreich aktualisiert.")