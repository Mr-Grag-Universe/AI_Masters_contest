import numpy as np
# import scipy as sp
import sys
from fractions import Fraction
from math import gcd
from random import shuffle, seed
from collections import defaultdict


'''
    новый план действий:
    1) генерируем все возможные целочисленные размеры для r-ок
    2) рекурсивно перебираем их комбинации, ища те, которые подходят
    3) поиск оптимизируем бинарным поиском - вместо этого ищем из последних i штук + меняем местами порядок приоритета
    4) при каждом погружении считаем метрику (свободную площадь)
    5) можно заранее отсеивать проигрышные варианты слишком большой суммарной площадью
'''


class Rect():
    c1 : dict
    c2 : dict
    # r : Fraction
    count = 0
    r_id : int

    @staticmethod
    def __find_fraction(x : float) -> Fraction:
        a = 10 ** len(str(x).split('.')[1])
        b = x*a
        g = gcd(a, b)
        return Fraction(b//g, a//g)
        

    def __init__(self, r_):
        self.r = max(r_, 1/r_)
        self.c1 = {'x': 0, 'y': 0}
        self.r_id = Rect.count
        Rect.count += 1
        f = Fraction.from_float(self.r).limit_denominator(1000)
        self.c2 = {'x' : f.numerator, 'y' : f.denominator}
        # print(f"Created: {self.c1} - {self.c2}, r: {self.r}, id: {self.r_id}")

    def move(self, point):
        self.c1['x'] += point[0]
        self.c2['x'] += point[0]
        self.c1['y'] += point[1]
        self.c2['y'] += point[1]
        # print(f"moved to c1: {self.c1}, c2: {self.c2}")

    def __eq__(self, other):
        return self.r == other.r
    
    def __ne__(self, other):
        return self.r != other.r
    
    def __lt__(self, other):
        return self.r < other.r

    def __gt__(self, other):
        return self.r > other.r

    def __str__(self):
        return f"<Rect object: (r: {self.r}, c1: {self.c1}, c2: {self.c2})>"

    def size(self):
        return (self.c2['y'] - self.c1['y'], self.c2['x'] - self.c1['x']) # (h, w)

    def get_coord_list(self) -> list:
        return [self.c1['x'], self.c1['y'], self.c2['x']-1, self.c2['y']-1]

    def setSize(self, size):
        self.c2 = {'x' : (self.c1['x'] + size[0]), 'y' : (self.c1['y'] + size[1])}

    def turn(self):
        self.c2['x'], self.c2['y'] = self.c1['x'] - self.c1['y'] + self.c2['y'], self.c1['y'] - self.c1['x'] + self.c2['x']
        self.r = 1/self.r

    def getSize(self):
        return (self.c2['y'] - self.c1['y'], self.c2['x'] - self.c1['x'])


class Column():
    isEmpty : bool

    def __init__(self, ind=0, size=1):
        self.ind = ind
        self.size = size
    
    def resize(self, new_size=1):
        self.size = new_size

    def setIndex(self, new_ind=0):
        self.ind = new_ind

    def empty(self):
        return self.isEmpty

class Row():
    isEmpty : bool

    def __init__(self, empty=True, ind=0, size=1):
        self.isEmpty = empty
        self.ind = ind
        self.size = size
    
    def resize(self, new_size=1):
        self.size = new_size

    def setIndex(self, new_ind=0):
        self.ind = new_ind

    def empty(self):
        return self.isEmpty


def get_cell(cols, rows, i, j, H, W):
    c_h, c_w = (0, 0) # max(, ) # cells[(cols[i], rows[j])]
    if i == len(cols)-1:
        c_w = W - cols[i]
    else:
        c_w = cols[i+1] - cols[i]
    
    if j == len(rows)-1:
        c_h = H - rows[j]
    else:
        c_h = rows[j+1] - rows[j]

    return c_h, c_w


def chose_rect_size(rect : Rect, field, cols, rows) -> tuple:
    H, W = len(field), len(field[0])
    r = 1/rect.r
    
    # немного туповатая проверка, но смысл в целом понятен
    for i in range(max(W, H), 1, -1):
        f = Fraction.from_float(r).limit_denominator(i)
        den, num = f.denominator, f.numerator
        d = abs(num/den-r)
        if d < 0.1 and min(den, num) < min(H,W) and max(den, num) < max(H, W):
            num, den = max(den, num), min(den, num)
            C = cols + [len(field[0])]
            R = rows + [len(field)]
            k1 = max(C) // den
            k2 = max(R) // num
            k = max(1, min(k1, k2) // 2)
            return (num * k, den * k)

    return None


def chose_min_rect_size(rect: Rect) -> tuple:
    r = rect.r
    for i in range(1, 100):
        f = Fraction.from_float(r).limit_denominator(i)
        den, num = f.denominator, f.numerator
        d = abs(num/den-r)
        if d < 0.1:
            return (num, den)


def append_to_field(rect : Rect, field, cols, rows, cells : dict = {}):
    h, w = rect.getSize()
    if abs(rect.r - 0.909090909) < 0.0001:
        pass # print(rect, "!!!!!!!")

    for i in range(len(cols)):
        for j in range(len(rows)):
            # если клетка cell не занята
            # проверка на случай, если у нас граница прямоугольника наложилась на 
            if cols[i] < len(field[0]) and rows[j] < len(field) and not field[rows[j]][cols[i]]:
                # print("cols and rows : ", cols[i], rows[j])
                # если она достаточно высокая

                # если недостаточно высокая, то попробуем объеденить с ячейками выше
                k = j
                H = 0 # c_h
                # print(f"k==j: {k}")
                while k < len(rows) and not field[rows[k]][cols[i]]:
                    # c_h, c_w = cells[(cols[i], rows[k])]
                    # считаем размеры текущей клетки
                    c_h, c_w = get_cell(cols, rows, i, k, len(field), len(field[0]))
                    # print("H: ", H, "c_w: ", c_w, "c_h: ", c_h)
                    
                    # может ли получиться так, что c_h < h - думаю нет
                    H += c_h
                    if H >= h:
                        break
                    k += 1
                
                if k == len(rows):
                    # print("edge!")
                    H = len(field) - rows[j]

                # print("j: ", j, "k: ", k, "rows: ", rows, "cols: ", cols)
                # print(f"H: {H}, h: {h}")
                # если не получилось собрать высоту
                if H < h:
                    continue

                # если ячейка нормальной высоты
                # собираем ширину
                l = i + 1
                W = c_w
                # проверяем все в выбранном диапазоне rows
                while l < len(cols) and not any(field[rows[t]][cols[l]] for t in range(j, min(k+1, len(rows)))):
                    # c_h, c_w = cells[(cols[l], rows[j])]
                    c_h, c_w = get_cell(cols, rows, l, j, len(field), len(field[0]))

                    # может ли получиться так, что c_h < h - думаю нет
                    W += c_w
                    if W >= w:
                        break
                    l += 1

                if l == len(cols):
                    W = len(field[0]) - cols[i]
                # print(f"W: {W}, w: {w}")
                if W < w:
                    continue

                # собрали клетки нормального размера
                # можно на их место добавлять прямойгольник
                # print(f"Вставляем {rect} в ({cols[i]}, {rows[j]})")
                if (cols[i] + w) not in cols and (cols[i] + w) < len(field[0]):
                    cols.append(cols[i] + w)
                    cols.sort()
                if (rows[j] + h) not in rows and (rows[j] + h) < len(field):
                    rows.append(rows[j] + h)
                    rows.sort()

                # забиваем поле True
                # print(rows[j], h, cols[i], w)
                for ind in range(rows[j], rows[j]+h):
                    # print(ind, end = '')
                    field[ind][cols[i]:cols[i]+w] = list(map(lambda x: True, range(cols[i],cols[i]+w)))

                rect.move((cols[i], rows[j]))
                if abs(rect.r - 0.909090909) < 0.0001:
                    pass # print(rect, "!!!!!!!", f"H: {H}, h: {h}, W: {W}, w: {w}")
                return rect, False

    if abs(rect.r - 0.909090909) < 0.0001:
        pass # print(rect, "!!!!!!!", f"error")
    return None, True


def printField(field):
    for line in field:
        if not (True in line):
            print("  ###  ", end='')
            continue
        print(' '.join(list(map(lambda x: '  |' if not x else '* |', line))))
        print('+'*(4*len(field[0])))


# генерирует все возможные комбинации сторон, удовленворяющие ограничениям
def generateSizes(r : float, H, W):
    if r < 1:
        r = 1/r

    r += 0.0001
    sizes = set()
    for i in range(1, min(H, W), 2):
        f = Fraction.from_float(r).limit_denominator(i)
        den, num = f.denominator, f.numerator
        d = abs(num/den-r)
        if d < 0.09 and num <= max(H, W) and den <= min(H, W):
            num, den = max(den, num), min(den, num)
            k1 = i // den
            k2 = i // num
            k = max(1, min(k1, k2))
            sizes.add((num * k, den * k))
    return sorted(list(sizes), reverse=True)


def tryCombo(rs, size_combo, H, W):
    field = [[False for _ in range(W)] for _ in range(H)]
    rects = []
    cols = [0]
    rows = [0]
    # print(len(rs), len(size_combo))
    for i in range(len(size_combo)):
        rect = Rect(rs[i])
        rect.setSize(size_combo[i])
        rects.append(rect)

    for i in range(len(rects)):
        err = True
        rect = rects[i]
        rr, err = append_to_field(rect, field, cols, rows)
        if err:
            rect.turn()
            rr, err = append_to_field(rect, field, cols, rows)
        rects[i] = rr
        # print(rect)

        if err == True:
            return None, True

    line = []
    rr = rects.copy()
    for r in rs:
        for i in range(len(rr)):
            if abs(r - rr[i].r) < 0.09 or abs(r - 1/rr[i].r) < 0.09:
                line += rr[i].get_coord_list()
                # print(rects[i])
                rr.pop(i)
                break

    # if line[-12] + line[-11] + line[-8]+line[-7] == 0:
    #     print(line)
    #     print("rects:")
    #     for rect in rects:
    #         print(rect)
    
    # print("line:", line)
    # если не все прямоугольники получилось распределить
    if len(rr) != 0:
        print("!!! there is some bad rect !!!")
        for rect in rr:
            print(rect)
        raise "rect determination problem"
    
    return line, False


def findOpt(rs, sizes, size_combo, H, W, selfS):
    if sizes == []:
        positions, err = tryCombo(rs, size_combo, H, W)
        if err == False:
            return positions, selfS, err
        else:
            return None, None, err

    # можно добавить бин поиск
    best_combo_positions = None
    minS = 0
    i = 0
    for size in sizes[0]:
        # если мы берём слишком большой размер - даже не пробуем подставлять
        if size[0]*size[1] > H*W-selfS:
            continue

        size_combo.append(size)
        positions, S, err = findOpt(rs, sizes[1:], size_combo, H, W, selfS+size[0]*size[1])
        size_combo.pop(-1)
        # нужно добавить сравниние площадей
        if err == False:
            i += 1
            if S > minS:
                best_combo_positions = positions
                minS = S

        if i > 2:
            return best_combo_positions, minS, False
        # else:
        #     continue
    
    if best_combo_positions:
        return best_combo_positions, minS, False # ([], True)
    else:
        return None, None, True


def unshuffle(pos, sh_r, order):
    undone_pos = pos.copy()
    for i in range(len(sh_r)):
        r = sh_r[i]
        ind = order[r][-1]
        order[r].pop(-1)
        undone_pos[ind*4 : (ind+1)*4] = pos[i*4 : (i+1)*4]

    return undone_pos


def solveCase(case) -> np.array:
    H, W = int(case[0]), int(case[1])
    cols = [0]
    rows = [0]
    rs = case[2:]

    # генерируем все возможные размеры для rects
    sizes = []
    for r in rs:
        sizes.append(generateSizes(r, H, W))

    # минимальные остаточные суммы
    # Ss = []
    # for i in range(len(sizes)-1):
    #     Ss = sum(np.asarray(sizes[i+1]).T[0])
    # Ss += [0]
    # print("sums: ", Ss)

    # print(sizes)
    
    Smax = 0
    position = None

    r_sizes = list(zip(rs, sizes))
    
    seed(42)
    for _ in range(3):
        order = defaultdict(list)
        for i in range(len(r_sizes)):
            order[r_sizes[i][0]].append(i)
            
        sh_r_sizes = r_sizes.copy()
        shuffle(sh_r_sizes)
        sh_r = [r for r, _ in sh_r_sizes]
        sh_sizes = [sizes for _, sizes in sh_r_sizes]
        # print(sh_r, sh_sizes)

        size_combo = []
        pos, S, err = findOpt(sh_r, sh_sizes, size_combo, H, W, 0)

        if S > Smax:
            position = unshuffle(pos, sh_r, order)
            Smax = S

        assert err == False

    return position


def solution(task) -> np.array:
    data_frame = []

    for case in task:
        # print(case)
        positions = solveCase(case)
        data_frame.append(positions)
        # break
        continue

        H, W = int(case[0]), int(case[1])
        field = [[False for _ in range(W)] for _ in range(H)]
        columns = [Column(0, W)]
        rows = [Row(0, H)]

        cols = [0]
        rows = [0]

        cells = {(0, 0) : (H, W)}

        rects = []
        for r in case[2:]:
            print(f"r: {r}")
            rects.append(Rect(r))
            size = chose_min_rect_size(rects[-1])
            rects[-1].setSize(size)
            print(rects[-1])
        
        rects.sort(reverse=False)

        # r in rects - r копия из списка - не влияет на список
        for i in range(len(rects)):
            rect = rects[i]
            # size = chose_rect_size(rect, field, cols, rows)
            # assert size is not None
            # rect.setSize(size)
            print(rect)

            # пытаемся добавить максимального размера
            rect, err = append_to_field(rect, field, cols, rows, cells)
            if err:
                rect.turn()
                rect, err = append_to_field(rect, field, cols, rows, cells)

            # если не получилось - пробуем с минимальным размером
            if err == False:
                rects[i] = rect
            else:
                rects[i], err = append_to_field(rects[i], field, cols, rows, cells)
                if err:
                    rects[i].turn()
                    rects[i], err = append_to_field(rects[i], field, cols, rows, cells)
            
            assert err == False

            printField(field)
        
        line = []
        print(case[2:])
        for r in case[2:]:
            for i in range(len(rects)):
                if abs(r - rects[i].r) < 0.09 or abs(r - 1/rects[i].r) < 0.09:
                    print(rects[i], r)
                    line += rects[i].get_coord_list()
                    rects.pop(i)
                    break

        if len(rects) != 0:
            print("!!! there is some bad rect !!!")
            for rect in rects:
                print(rect)
            raise "dfddf"
        data_frame.append(line)

    # print(data_frame)
    return data_frame


task = np.genfromtxt(sys.argv[1], delimiter=",", skip_header=1)
# print(task)


sol = solution(task)
sol = np.asarray(sol, dtype=str)
# print(sol)

header = (', '.join([f'X{i+1}min, Y{i+1}min, X{i+1}max, Y{i+1}max' for i in range(len(sol[0]) // 4)])).split(', ')
# print(header)
sol = np.insert(sol, 0, np.asarray(header, dtype=str), axis=0)
# print(sol)
np.savetxt("solution.csv", sol, delimiter=",", fmt="%s")

# рекурсивный поиск по всем размерам бин поиском

