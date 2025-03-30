import sys
import sqlite3
from PIL import Image, ImageOps
from PyQt5.QtCore import Qt
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QInputDialog, QPushButton, QListWidget, QDateEdit, QTimeEdit,\
    QListWidgetItem, QFileDialog, QMessageBox
from PyQt5.QtGui import QIcon

connector = sqlite3.connect('users_files.db')
cur = connector.cursor()
exe = cur.execute("""SELECT * FROM files""").fetchall()
names = list(map(lambda x: x[1], exe))  # имена всех созданных файлов
ides = list(map(lambda x: x[0], exe))
id1 = 1
if bool(ides):
    id1 = ides[-1] + 1

# ниже функция, сравнивающая: 1) дэдлайн пункта и время сейчас, чтобы определить прошел дэдлайн или нет
# (если flag = True) 2) дэдлайны двух пунктов, чтобы определить какой пункт должен находиться раньше в self.list
# (перечне пунктов библиотеки QListWidget)


def check(s_time, s_date, flag, f_time=[], f_date=[]):
    if flag:
        now = str(datetime.datetime.now())
        f_time = now.split(' ')[1].split('.')[0].split(':')[:2]
        f_date = now.split(' ')[0].split('-')
    n = 0
    while n < 3:
        if int(s_date[n]) != int(f_date[n]):  # поиск первого расхождения по дате (например, разные года)
            break
        n += 1
    if n == 3:
        n = 0
        while n < 2:
            if int(s_time[n]) != int(f_time[n]):  # поиск первого расхождения по времени
                break
            n += 1
        return int(s_time[n]) < int(f_time[n])  # сравниваю по этому расхождению
    return int(s_date[n]) < int(f_date[n])

# ниже доп. класс, наследуемый от QListWidgetItem, чтобы задать сравнение элементов сначала по дэдлайну, если он
# одинаковый, то по алфавиту


class ListWidgetItem(QListWidgetItem):
    def __lt__(self, other):
        time1 = self.text().split('|')[1].split(' ')[1].split(':')
        data1 = self.text().split('|')[1].split(' ')[3].split('.')
        time2 = other.text().split('|')[1].split(' ')[1].split(':')
        data2 = other.text().split('|')[1].split(' ')[3].split('.')
        if time1 == time2 and data1 == data2:  # проверка: одинаковы ли дэдлайны
            return self.text().split('|')[0] < other.text().split('|')[1]
        return check(time1, data1, False, time2, data2)


class Example(QMainWindow):
    def __init__(self):
        super().__init__()

        self.name = ''
        self.points = []
        self.action = ''
        self.ok = True
        self.time = QTimeEdit(self)
        self.date = QDateEdit(self)
        self.list = QListWidget(self)
        self.saved = True
        self.current_text = ''

        self.setui()

    def setui(self):
        self.setFixedSize(900, 700)

        self.action, self.ok = QInputDialog.getItem(self, 'Выберите действие', 'Что вы хотите сделать?',
                                                    ("Создать файл", "Открыть файл"), 0, False)

        self.time = QTimeEdit(self)  # ниже создается интерфейса
        self.time.resize(448, 31)
        self.time.move(1, 2)

        self.date = QDateEdit(self)
        self.date.resize(448, 31)
        self.date.move(451, 2)

        self.list = QListWidget(self)
        self.list.resize(898, 614)
        self.list.move(1, 35)

        self.dialog()  # функция, в которой либо создается имя файла, либо загружается информация созданного файла

        btn1 = QPushButton('Добавить пункт(ы)', self)
        btn1.resize(198, 40)
        btn1.move(3, 650)

        btn1.clicked.connect(self.choose)

        btn2 = QPushButton('Отметить сделанным(и)', self)
        btn2.resize(198, 40)
        btn2.move(202, 650)
        btn2.clicked.connect(self.complete)

        btn3 = QPushButton('Изменить', self)
        btn3.resize(198, 40)
        btn3.move(401, 650)
        btn3.clicked.connect(self.change)

        btn4 = QPushButton('Удалить', self)
        btn4.resize(198, 40)
        btn4.move(600, 650)
        btn4.clicked.connect(self.delete)

        btn = QPushButton('Сохранить', self)
        btn.resize(99, 40)
        btn.move(799, 650)
        btn.clicked.connect(self.save)

    def dialog(self):
        global id1

        self.name = ''
        if self.ok:
            if self.action == "Создать файл":  # создание имени файла
                self.name, ok2 = QInputDialog.getText(self, 'Введите имя файла', 'Как вы хотите назвать файл?')
                if self.name in names:
                    QMessageBox.information(self, '', 'Файл с таким именем уже существует')
                    self.dialog()
                elif self.name == '':  # если пользователь не ввел имя, оно создается по умолчанию
                    self.name = 'file'
                    n = 1
                    while self.name in names:
                        if n > 1:
                            i = 0
                            while not self.name[i].isdigit():
                                i += 1
                            self.name = self.name[:i] + str(n)
                        else:
                            self.name += str(n)
                        n += 1
                self.points = []
                self.saved = False
            else:
                if not bool(names):
                    QMessageBox.information(self, '', 'Ёще не создан ни один файл')
                    self.setui()
                else:
                    self.name, ok1 = QInputDialog.getItem(self, 'Выберите имя файла', 'Какой файл вы хотите открыть?',
                                                          tuple(names), 0, False)
                    execute = cur.execute(f"""SELECT id, text FROM files WHERE name = '{self.name}'""").fetchall()
                    id1 = execute[0][0]  # id файла в БД
                    self.points = execute[0][1].split('\n')  # пункты файла
                    for i in self.points:
                        if i.split('|')[2] != '':  # если есть картинка
                            icon = QIcon(i.split('|')[2].strip())
                            item = ListWidgetItem(icon, '|'.join(i.split('|')[:2]).strip() + ' |')
                        else:  # если нет
                            item = ListWidgetItem(i)
                        item.setCheckState(Qt.Unchecked)  # добавление квадратика, чтобы можно было пункты помечать галочкой
                        self.list.addItem(item)  # добавление элемента
                        self.list.sortItems()  # сортировка
                        t = i.split('|')[1].split(' ')[1]  # для кнопки "Изменить"; дэдлайн до изменения
                        d = i.split('|')[1].split(' ')[3]
                        if check(t.split(':'), sorted(d.split('.'), reverse=True), True):  # проверка на дэдлайн
                            item.setBackground(Qt.red)
                    self.list.sortItems()
                    self.saved = True

            self.setWindowTitle(self.name)
            self.current_text = ''
        else:  # если пользователь нажал "Отмена", то приложение закрывается
            sys.exit(app.exec_())

    def save(self):  # кнопка "Сохранить"
        global id1

        if not bool(self.points):
            QMessageBox.information(self, '', 'Вы не написали ни одного пункта')
        else:
            action, ok = QInputDialog.getItem(self, 'Выберите действие', 'Что вы хотите сделать?',
                                              ("Сохранить", "Сохранить и создать новый файл", "Сохранить и выйти"),
                                              0, False)
            if ok:
                points = '\n'.join(self.points)
                if self.saved:  # не первое сохранение (изменение уже добавленной строчки таблицы)
                    cur.execute(f"""UPDATE files SET text = '{points}' WHERE id = {id1}""")
                else:  # первое сохранение (создание строчки)
                    cur.execute(f"""INSERT INTO files VAlUES ({id1}, '{self.name}', '{points}')""")
                    self.saved = True
                connector.commit()
                if action == "Сохранить и создать новый файл":  # сохранение и появление первого даилогового окна
                    id1 += 1
                    names.append(self.name)
                    self.dialog()
                    self.list.clear()
                elif action == "Сохранить и выйти":  # сохранение и закрытие приложения
                    names.append(self.name)
                    sys.exit(app.exec_())

    def write(self):  # "Написать вручную"
        tex, ok_pressed = QInputDialog.getText(self, "Введите текст", "Что вы хотите запланировать?")
        if ok_pressed:
            if '|' in tex:  # проверка, что не используется этот символ (он помогает мне отделить время от текста)
                QMessageBox.information(self, '', 'Не используйте, пожалйста, символ "|"')
                self.write()
            if tex == '':  # если пользователь ничего не ввел, то появляется сообщение и функция запускается заново
                QMessageBox.information(self, '', 'Введите, пожалуйста, что вы хотите запланировать')
                self.write()
            elif self.current_text == tex:
                QMessageBox.information(self, '', 'Вы ввели то же, что было этого')
            elif tex != '':
                if self.current_text == '':
                    t = self.time.text()  # дэдлайн (время и дата)
                    d = self.date.text()
                else:
                    t = self.current_text.split('|')[1].split(' ')[1]  # для кнопки "Изменить"; дэдлайн до изменения
                    d = self.current_text.split('|')[1].split(' ')[3]
                item = ListWidgetItem(f'{tex.strip()}  | {t} - {d} |')
                item.setCheckState(Qt.Unchecked)  # добавление квадратика, чтобы можно было пункты помечать галочкой
                self.list.addItem(item)  # добавление элемента
                self.list.sortItems()  # сортировка
                if check(t.split(':'), sorted(d.split('.'), reverse=True), True):  # проверка на дэдлайн
                    item.setBackground(Qt.red)
                self.points.append(f'{tex.strip()}  | {t} - {d} |')  # добавление пункта в список с пунктами
        elif self.current_text != '':
            self.change()
        else:
            self.choose()

    # ниже некоторые вещи будут совпадать

    def txt(self):  # "Скопировать с файла (.txt)"
        file_name, ok = QFileDialog.getOpenFileName(self, 'Выберите непустой файл', '', 'Text files (*.txt)')
        if ok:
            file = open(file_name, 'r', encoding='utf-8').read().split('\n')
            if file[0] == '':  # проверка, что файл не пустой
                QMessageBox.information(self, '', 'Вы выбрали пустой файл')
                self.txt()
            else:
                for i in file:
                    if '|' in i:
                        QMessageBox.information(self, '', 'В файле обнаружен символ "|"')
                        self.txt()
                    elif i != '':
                        t = self.time.text()
                        d = self.date.text()
                        item = ListWidgetItem(f'{i.strip()}  | {t} - {d} |')
                        item.setCheckState(Qt.Unchecked)
                        self.list.addItem(item)
                        if check(t.split(':'), sorted(d.split('.'), reverse=True), True):
                            item.setBackground(Qt.red)
                        self.points.append(f'{i.strip()}  | {t} - {d} |')
                        self.list.sortItems()
        elif self.current_text != '':
            self.change()
        else:
            self.choose()

    def image(self):
        tex, ok_pressed = QInputDialog.getText(self, "Введите текст", "Что вы хотите запланировать?")
        if ok_pressed:
            if tex == '':
                QMessageBox.information(self, '', 'Введите, пожалуйста, что вы хотите запланировать')
                self.image()
            elif self.current_text == tex:
                QMessageBox.information(self, '', 'Вы ввели то же, что было этого')
            elif '|' in tex:
                QMessageBox.information(self, '', 'Не используйте, пожалйста, символ "|"')
                self.image()
            else:
                file_name, ok1 = QFileDialog.getOpenFileName(self, 'Выберите картинку', '',
                                                             'Картинка (*.png);;Картинка (*.jpg)')
                if ok1:
                    action, ok = QInputDialog.getItem(
                        self, "Выберите действие", "Как вы хотите изменить картинку?",
                        ("Никак", "Сделать черно-белой", "Негатив"), 0, False)
                    if ok:  # изменение картинки
                        file = Image.open(file_name)
                        n = ''
                        try:
                            while True:
                                if n == '':
                                    Image.open('help.png')
                                    n = 1
                                else:
                                    Image.open(f'help{n}.png')
                                    n += 1
                        except FileNotFoundError:
                            pass
                        if action == "Сделать черно-белой":
                            ImageOps.grayscale(file).save(f'help{n}.png')
                        elif action == "Негатив":
                            ImageOps.invert(file).save(f'help{n}.png')
                        else:
                            file.save(f'help{n}.png')
                        icon = QIcon(f'help{n}.png')
                        if self.current_text == '':
                            t = self.time.text()
                            d = self.date.text()
                        else:
                            t = self.current_text.split('|')[1].split(' ')[1]
                            d = self.current_text.split('|')[1].split(' ')[3]
                        item = ListWidgetItem(icon, f'{tex.strip()}   | {t} - {d} |')
                        item.setCheckState(Qt.Unchecked)
                        self.list.addItem(item)
                        self.list.sortItems()
                        if check(t.split(':'), sorted(d.split('.'), reverse=True), True):
                            item.setBackground(Qt.red)
                        self.points.append(f'{tex.strip()}  | {t} - {d} | help{n}.png')
        elif self.current_text != '':
            self.change()
        else:
            self.choose()

    def choose(self):  # кнопка "Добавить пункт(ы)"
        action, ok = QInputDialog.getItem(self, "Выберите действие", "Как вы хотите добавить пункт?",
                                          ("Написать вручную", "Скопировать с файла (.txt)",
                                           "Написать вручную + изображение"), 0, False)
        if ok:
            if action == 'Написать вручную':
                self.write()
            elif action == 'Скопировать с файла (.txt)':
                self.txt()
            else:
                self.image()

    def complete(self):  # кнопка "Отметить сделанным(и)"
        count = 0
        n = 0
        for i in range(self.list.count()):  # считаю количество помеченных пунктов
            if self.list.item(n).checkState() == 2:
                count += 1
            n += 1
        if count == 0:  # если выбрано ноль или больше 1 пунктов
            QMessageBox.information(self, '', 'Выберите один пункт, который хотите отметить выполненным')
        else:
            for i in range(self.list.count()):
                if self.list.item(i).checkState() == 2:  # проверка, что пункт выбран (по галочке)
                    self.list.item(i).setBackground(Qt.green)  # если помечен, то выделяется зеленым, как сделанный

    def delete(self):  # кнопка "Удалить"
        count = 0
        n = 0
        for i in range(self.list.count()):  # считаю количество помеченных пунктов
            if self.list.item(n).checkState() == 2:
                count += 1
            n += 1
        if count == 0:  # если выбрано ноль или больше 1 пунктов
            QMessageBox.information(self, '', 'Выберите один пункт, который хотите удалить')
        else:
            n = 0
            for i in range(self.list.count()):
                if self.list.item(n).checkState() == 2:
                    self.list.takeItem(n)  # если помечен, то пункт удаляется
                    del self.points[n]
                    n -= 1
                n += 1

    def change(self):  # кнопка "Изменить"
        n = 0
        self.current_text = ''
        count = 0
        for i in range(self.list.count()):  # считаю количество помеченных пунктовD
            if self.list.item(n).checkState() == 2:
                count += 1
            n += 1
        n = 0
        if count > 1 or count == 0:  # если выбрано ноль или больше 1 пунктов
            QMessageBox.information(self, '', 'Выберите один пункт, который хотите изменить')
        else:
            for i in range(self.list.count()):  # получаю текст выбранного пункта
                if self.list.item(n).checkState() == 2:
                    self.current_text = self.list.takeItem(n).text()
                    n -= 1
                n += 1
            answer = QMessageBox.question(self, "", "Вы хотите добавить изображение?")  # окно с вопросом
            if answer == QMessageBox.Yes:
                self.image()
            else:
                self.write()
        self.current_text = ''


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    ex = Example()
    ex.show()
    sys.exit(app.exec_())
connector.close()
