import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLineEdit, QFormLayout, QGroupBox,QMessageBox)


from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QIntValidator
from PyQt5.QtCore import Qt, QRect, QPoint
import xml.etree.ElementTree as ET

class ImageAnnotator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_path = None
        self.boxes = []
        self.drawing = False
        self.draw_mode = False
        self.edit_mode = False
        self.start_point = None
        self.end_point = None
        self.current_pixmap = None
        self.selected_box = None
        self.resize_handle = None
        self.move_start = None

    def initUI(self):
        self.setWindowTitle('Image Annotator')
        self.setGeometry(100, 100, 1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side - Image and buttons
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout, 2)

        self.image_label = QLabel()
        left_layout.addWidget(self.image_label)

        button_layout = QHBoxLayout()
        left_layout.addLayout(button_layout)

        load_button = QPushButton('Load Image')
        load_button.clicked.connect(self.load_image)
        button_layout.addWidget(load_button)

        self.draw_button = QPushButton('Draw Bounding Box')
        self.draw_button.setCheckable(True)
        self.draw_button.clicked.connect(self.toggle_draw_mode)
        button_layout.addWidget(self.draw_button)

        self.edit_button = QPushButton('Edit Bounding Box')
        self.edit_button.setCheckable(True)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        button_layout.addWidget(self.edit_button)

        delete_button = QPushButton('Delete Selected Box')
        delete_button.clicked.connect(self.delete_selected_box)
        button_layout.addWidget(delete_button)

        save_button = QPushButton('Save Annotations')
        save_button.clicked.connect(self.save_annotations)
        button_layout.addWidget(save_button)

        # Right side - Edit box
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout, 1)

        self.edit_box = QGroupBox("Edit Bounding Box")
        self.edit_box.setEnabled(False)
        right_layout.addWidget(self.edit_box)

        edit_form = QFormLayout()
        self.edit_box.setLayout(edit_form)

        self.x_input = QLineEdit()
        self.y_input = QLineEdit()
        self.width_input = QLineEdit()
        self.height_input = QLineEdit()

        for input_field in [self.x_input, self.y_input, self.width_input, self.height_input]:
            input_field.setValidator(QIntValidator())
            input_field.textChanged.connect(self.update_box_from_input)

        edit_form.addRow("X:", self.x_input)
        edit_form.addRow("Y:", self.y_input)
        edit_form.addRow("Width:", self.width_input)
        edit_form.addRow("Height:", self.height_input)

        apply_button = QPushButton("Apply Changes")
        apply_button.clicked.connect(self.apply_box_changes)
        edit_form.addRow(apply_button)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            self.image_path = file_path
            self.current_pixmap = QPixmap(file_path)
            self.image_label.setPixmap(self.current_pixmap)
            self.image_label.setFixedSize(self.current_pixmap.width(), self.current_pixmap.height())

    def toggle_draw_mode(self):
        self.draw_mode = self.draw_button.isChecked()
        if self.draw_mode:
            self.draw_button.setText('Cancel Drawing')
            self.edit_button.setChecked(False)
            self.edit_mode = False
        else:
            self.draw_button.setText('Draw Bounding Box')
        self.selected_box = None
        self.update_image()
        self.update_edit_box()

    def toggle_edit_mode(self):
        self.edit_mode = self.edit_button.isChecked()
        if self.edit_mode:
            self.edit_button.setText('Cancel Editing')
            self.draw_button.setChecked(False)
            self.draw_mode = False
        else:
            self.edit_button.setText('Edit Bounding Box')
        self.selected_box = None
        self.update_image()
        self.update_edit_box()

    def mousePressEvent(self, event):
        if not self.image_path:
            return
        
        pos = event.pos() - self.image_label.pos()
        
        if self.draw_mode and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = pos
            self.end_point = pos
        elif self.edit_mode and event.button() == Qt.LeftButton:
            self.selected_box = None
            for i, box in enumerate(self.boxes):
                if QRect(box[0], box[1]).contains(pos):
                    self.selected_box = i
                    self.resize_handle = self.get_resize_handle(pos, box)
                    if not self.resize_handle:
                        self.move_start = pos
                    break
        self.update_image()
        self.update_edit_box()

    def mouseMoveEvent(self, event):
        if not self.image_path:
            return
        
        pos = event.pos() - self.image_label.pos()
        
        if self.drawing:
            self.end_point = pos
        elif self.edit_mode and self.selected_box is not None:
            box = list(self.boxes[self.selected_box])
            if self.resize_handle:
                if 'top' in self.resize_handle:
                    box[0].setY(pos.y())
                elif 'bottom' in self.resize_handle:
                    box[1].setY(pos.y())
                if 'left' in self.resize_handle:
                    box[0].setX(pos.x())
                elif 'right' in self.resize_handle:
                    box[1].setX(pos.x())
            elif self.move_start:
                delta = pos - self.move_start
                box[0] += delta
                box[1] += delta
                self.move_start = pos
            self.boxes[self.selected_box] = tuple(box)
        self.update_image()
        self.update_edit_box()

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            self.boxes.append((self.start_point, self.end_point))
        self.move_start = None
        self.resize_handle = None
        self.update_image()
        self.update_edit_box()

    def get_resize_handle(self, pos, box):
        handle_size = 6
        rect = QRect(box[0], box[1])
        if abs(pos.x() - rect.left()) < handle_size:
            if abs(pos.y() - rect.top()) < handle_size:
                return 'topleft'
            elif abs(pos.y() - rect.bottom()) < handle_size:
                return 'bottomleft'
            elif rect.top() < pos.y() < rect.bottom():
                return 'left'
        elif abs(pos.x() - rect.right()) < handle_size:
            if abs(pos.y() - rect.top()) < handle_size:
                return 'topright'
            elif abs(pos.y() - rect.bottom()) < handle_size:
                return 'bottomright'
            elif rect.top() < pos.y() < rect.bottom():
                return 'right'
        elif rect.left() < pos.x() < rect.right():
            if abs(pos.y() - rect.top()) < handle_size:
                return 'top'
            elif abs(pos.y() - rect.bottom()) < handle_size:
                return 'bottom'
        return None

    def update_image(self):
        if self.current_pixmap:
            temp_pixmap = self.current_pixmap.copy()
            painter = QPainter(temp_pixmap)
            self.draw_boxes(painter)
            painter.end()
            self.image_label.setPixmap(temp_pixmap)

    def draw_boxes(self, painter):
        for i, box in enumerate(self.boxes):
            if i == self.selected_box:
                painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
                painter.setBrush(QColor(0, 255, 0, 30))
            else:
                painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
                painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRect(box[0], box[1]))

        if self.drawing:
            painter.setPen(QPen(QColor(255, 0, 0, 128), 2, Qt.SolidLine))
            painter.setBrush(QColor(255, 0, 0, 30))
            painter.drawRect(QRect(self.start_point, self.end_point))

    def delete_selected_box(self):
        if self.selected_box is not None:
            del self.boxes[self.selected_box]
            self.selected_box = None
            self.update_image()
            self.update_edit_box()

    def update_edit_box(self):
        if self.selected_box is not None and 0 <= self.selected_box < len(self.boxes):
            self.edit_box.setEnabled(True)
            box = self.boxes[self.selected_box]
            self.x_input.setText(str(min(box[0].x(), box[1].x())))
            self.y_input.setText(str(min(box[0].y(), box[1].y())))
            self.width_input.setText(str(abs(box[0].x() - box[1].x())))
            self.height_input.setText(str(abs(box[0].y() - box[1].y())))
        else:
            self.edit_box.setEnabled(False)
            for input_field in [self.x_input, self.y_input, self.width_input, self.height_input]:
                input_field.clear()

    def update_box_from_input(self):
        if self.selected_box is not None and 0 <= self.selected_box < len(self.boxes):
            try:
                x = int(self.x_input.text())
                y = int(self.y_input.text())
                width = int(self.width_input.text())
                height = int(self.height_input.text())
                self.boxes[self.selected_box] = (QPoint(x, y), QPoint(x + width, y + height))
                self.update_image()
            except ValueError:
                pass  # Ignore invalid input

    def apply_box_changes(self):
        self.update_box_from_input()
        self.update_edit_box()


    def save_annotations(self):
        if not self.image_path or not self.boxes:
            return

        # Get the directory and filename of the original image
        image_dir = os.path.dirname(self.image_path)
        image_filename = os.path.splitext(os.path.basename(self.image_path))[0]
        
        # Create the XML filename
        xml_filename = f"{image_filename}.xml"
        xml_path = os.path.join(image_dir, xml_filename)

        root = ET.Element("annotation")

        filename = ET.SubElement(root, "filename")
        filename.text = os.path.basename(self.image_path)

        size = ET.SubElement(root, "size")
        width = ET.SubElement(size, "width")
        height = ET.SubElement(size, "height")
        pixmap = self.current_pixmap
        width.text = str(pixmap.width())
        height.text = str(pixmap.height())

        for i, box in enumerate(self.boxes):
            object_elem = ET.SubElement(root, "object")
            name = ET.SubElement(object_elem, "name")
            name.text = f"object_{i+1}"

            bndbox = ET.SubElement(object_elem, "bndbox")
            xmin = ET.SubElement(bndbox, "xmin")
            ymin = ET.SubElement(bndbox, "ymin")
            xmax = ET.SubElement(bndbox, "xmax")
            ymax = ET.SubElement(bndbox, "ymax")

            xmin.text = str(min(box[0].x(), box[1].x()))
            ymin.text = str(min(box[0].y(), box[1].y()))
            xmax.text = str(max(box[0].x(), box[1].x()))
            ymax.text = str(max(box[0].y(), box[1].y()))

        tree = ET.ElementTree(root)
        tree.write(xml_path)

        QMessageBox.information(self, "Save Annotations", f"Annotations saved to {xml_path}")
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageAnnotator()
    ex.show()
    sys.exit(app.exec_())