import sys
import os
import subprocess
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, QCheckBox, QFileDialog, 
                               QTextEdit, QMessageBox)

class Blend2JsonGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blend2Json GUI")
        self.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # File Selection
        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select .blend file...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_path)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)
        
        # Options
        self.check_file = QCheckBox("Check File Validity Only (-c)")
        self.compact_output = QCheckBox("Compact Output (--compact-output)")
        self.no_old_addresses = QCheckBox("No Old Addresses (--no-old-addresses)")
        self.no_fake_old_addresses = QCheckBox("Disable Fake Old Addresses (--no-fake-old-addresses)")
        self.full_data = QCheckBox("Full Data (--full-data)")
        self.full_dna = QCheckBox("Full DNA (--full-dna)")
        self.raw_bblock = QCheckBox("Raw BBlock (--raw-bblock)")
        
        layout.addWidget(self.check_file)
        layout.addWidget(self.compact_output)
        layout.addWidget(self.no_old_addresses)
        layout.addWidget(self.no_fake_old_addresses)
        layout.addWidget(self.full_data)
        layout.addWidget(self.full_dna)
        layout.addWidget(self.raw_bblock)
        
        # Filter Data
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Data (comma-separated):"))
        self.filter_data = QLineEdit()
        self.filter_data.setPlaceholderText("e.g. name,id")
        filter_layout.addWidget(self.filter_data)
        layout.addLayout(filter_layout)

        # Run Button
        self.run_btn = QPushButton("Convert to JSON")
        self.run_btn.clicked.connect(self.run_conversion)
        layout.addWidget(self.run_btn)
        
        # Output Log
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        
        self.setLayout(layout)

        # Check if a file argument was passed
        if len(sys.argv) > 1:
            self.file_path.setText(sys.argv[1])

    def browse_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select .blend file", "", "Blender Files (*.blend)")
        if fname:
            self.file_path.setText(fname)

    def run_conversion(self):
        input_file = self.file_path.text()
        if not input_file:
            QMessageBox.warning(self, "Error", "Please select a .blend file.")
            return
            
        script_path = os.path.join(os.path.dirname(__file__), "blend2json.py")
        cmd = [sys.executable, script_path, input_file]
        
        if self.check_file.isChecked():
            cmd.append("-c")
        if self.compact_output.isChecked():
            cmd.append("--compact-output")
        if self.no_old_addresses.isChecked():
            cmd.append("--no-old-addresses")
        if self.no_fake_old_addresses.isChecked():
            cmd.append("--no-fake-old-addresses")
        if self.full_data.isChecked():
            cmd.append("--full-data")
        if self.full_dna.isChecked():
            cmd.append("--full-dna")
        if self.raw_bblock.isChecked():
            cmd.append("--raw-bblock")
        
        filter_val = self.filter_data.text().strip()
        if filter_val:
            cmd.append(f"--filter-data={filter_val}")
            
        self.log_output.append(f"Running: {' '.join(cmd)}")
        
        try:
            # Run in the same python environment
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # We want to keep the GUI responsive, but for simplicity in this script we wait.
            # For better UX, QProcess could be used, but this is sufficient for a tool.
            stdout, stderr = process.communicate()
            
            if stdout:
                self.log_output.append("OUTPUT:\n" + stdout)
            if stderr:
                self.log_output.append("ERROR:\n" + stderr)
                
            if process.returncode == 0:
                self.log_output.append("SUCCESS")
                if not self.check_file.isChecked():
                     QMessageBox.information(self, "Success", f"Conversion complete.\nJSON should be next to input file.")
            else:
                self.log_output.append(f"Process exited with code {process.returncode}")
                
        except Exception as e:
            self.log_output.append(f"Exception: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = Blend2JsonGUI()
    gui.show()
    sys.exit(app.exec())
