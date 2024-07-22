import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect
import xml.etree.ElementTree as ET

class ImageAnnotator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.image_path = None
        self.boxes = []
        self.drawing = False
        self.draw_mode = False
        self.start_point = None
        self.end_point = None
        self.current_pixmap = None

    def initUI(self):
        self.setWindowTitle('Image Annotator')
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.image_label = QLabel()
        main_layout.addWidget(self.image_label)

        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        load_button = QPushButton('Load Image')
        load_button.clicked.connect(self.load_image)
        button_layout.addWidget(load_button)

        self.draw_button = QPushButton('Draw Bounding Box')
        self.draw_button.setCheckable(True)
        self.draw_button.clicked.connect(self.toggle_draw_mode)
        button_layout.addWidget(self.draw_button)

        save_button = QPushButton('Save Annotations')
        save_button.clicked.connect(self.save_annotations)
        button_layout.addWidget(save_button)

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
        else:
            self.draw_button.setText('Draw Bounding Box')

    def mousePressEvent(self, event):
        if self.image_path and self.draw_mode and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos() - self.image_label.pos()
            self.end_point = self.start_point
            self.update_image()

    def mouseMoveEvent(self, event):
        if self.drawing:
            self.end_point = event.pos() - self.image_label.pos()
            self.update_image()

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            self.end_point = event.pos() - self.image_label.pos()
            self.boxes.append((self.start_point, self.end_point))
            self.update_image()

    def update_image(self):
        if self.current_pixmap:
            temp_pixmap = self.current_pixmap.copy()
            painter = QPainter(temp_pixmap)
            self.draw_boxes(painter)
            painter.end()
            self.image_label.setPixmap(temp_pixmap)

    def draw_boxes(self, painter):
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        painter.setPen(pen)

        for box in self.boxes:
            painter.drawRect(QRect(box[0], box[1]))

        if self.drawing:
            painter.setPen(QPen(QColor(255, 0, 0, 128), 2, Qt.SolidLine))
            painter.setBrush(QColor(255, 0, 0, 30))
            painter.drawRect(QRect(self.start_point, self.end_point))

    def save_annotations(self):
        if not self.image_path or not self.boxes:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Annotations", "", "XML Files (*.xml)")
        if file_path:
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
            tree.write(file_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ImageAnnotator()
    ex.show()
    sys.exit(app.exec_())