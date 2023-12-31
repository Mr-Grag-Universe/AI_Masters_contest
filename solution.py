'''
    финальный сабмит (если пройдёт проверку по времени конечно)
    по итогу я изменил только количество итераций для рандома + соотношение для уменьшения размера выборки рамеров
    (ничего не менял)
    ну и повырезал лишние функции, чтобы вам голову не парить
'''

import numpy as np
import scipy as sp
import sys
from fractions import Fraction
from math import gcd
from random import shuffle, seed, choice
from collections import defaultdict, deque
import time
import copy
import bisect
import itertools

def benchmark(func):
    ''' декоратор-таймер '''

    def wrapper(*args, **kwargs):
        start = time.time()
        x = func(*args, **kwargs)
        end = time.time()
        delta_t = (end - start)
        m = int(delta_t)//60
        s = int(delta_t)%60
        ms = int(1000*(delta_t-m*60-s))
        print(f"[*] Время выполнения: {m}:{s}:{ms}")
        return x
    return wrapper

# для таймирования в многопоточке
def wrapped_func(*args, **kwargs):
    return benchmark(solveCaseFullRand)(*args, **kwargs)


'''
    ЗАМЕТКИ по ходу работы
    описан процесс течения мысли по древу

    новый план действий:
    1) генерируем все возможные целочисленные размеры для r-ок
    2) рекурсивно перебираем их комбинации, ища те, которые подходят
    3) поиск оптимизируем бинарным поиском (мб потом реализую что-то такое. можно посмотреть, как байесовский оптимизатор работает)
        * вместо этого ищем из последних i штук + меняем местами порядок приоритета (рандомно перетасовываем пару раз)
    4) при каждом погружении считаем метрику (свободную/занятую площадь)
    5) можно заранее отсеивать проигрышные варианты слишком большой суммарной площадью
    6) начинаем с максимальных размеров
    7) сортируем по площади фигуры

    Стратегия заполнения простая и описана вот тут : https://www.codeproject.com/Articles/210979/Fast-optimizing-rectangle-packing-algorithm-for-bu
    По сути просто перебираем n-ое колечество кобинаций размеров, пытаясь скомпоновать их этим алгоритмом

    как выяснилось эксперементальным путём:
    * сортировка в порядке убывания площади - плохая идея - NOOOOOO
    * увеличение числа shuffle - перестановок порядков прямоугольников - хорошая идея (2->3 : 2:27->3:50 : 875->798) YESS
    * добавление рандомного выбора размера после нахождения максимального рабочего - хорошая идея? (3:50->3:13 : 798->744) не знаю почему стало работать быстрее)) YESSS
    * 

    можно попробовать вариации алгоритма на тему не сляпывать фигуры, а наоборот разносить
    или ставить так, чтобы оставлять как можно больше свободного места

    долбаное проклятие размерности!!!
    пришлось переделывать. сейчас у меня всё решает великий рандом - отсеиваем минимум признаков

    оказалось, что полный рандом - довольно эффективная стратегия

    подводя итоги - по выдимому я выбрал неверную стратегию, разделяя подбор комбинации размеров и их размещение.
    путём подгона и теста разных алгоритмов вставки/упаковки за разумное время (сильно ограниченное подбором/перебором размеров)
    получить меньше 600 очков я не смог
    по видимому надо было думать над каким нибудь генетическим алгоритмом или ещё что-то комбинированное, 
    но я уже не успею это придумать и реализовать

    посмотрел на википеции и по репозиториям гитхаба решения (не знаю, почему сразу так не сделал).
    глаза на лоб лезут. там задачи все со статическими размерами, но мне страшно. люди пишут НИРы по этим темам
    ну и задачка...

    финальный сабмит. решил оставить немного коментариев
'''


class Rect():
    __slots__ = ("r", "c1", "c2")

    @staticmethod
    def __find_fraction(x : float) -> Fraction:
        a = 10 ** len(str(x).split('.')[1])
        b = x*a
        g = gcd(a, b)
        return Fraction(b//g, a//g)
        

    def __init__(self, r_):
        self.r = max(r_, 1/r_)
        self.c1 = {'x': 0, 'y': 0}
        f = Fraction.from_float(self.r).limit_denominator(1000)
        self.c2 = {'x' : f.denominator, 'y' : f.numerator}
        # print(f"Created: {self.c1} - {self.c2}, r: {self.r}, id: {self.r_id}")

    def move(self, point):
        self.c1['x'] += point[0]
        self.c2['x'] += point[0]
        self.c1['y'] += point[1]
        self.c2['y'] += point[1]
        # print(f"moved to c1: {self.c1}, c2: {self.c2}")

    def __eq__(self, other):
        return abs(self.r - other.r) < 0.09 or abs(self.r - 1/other.r) < 0.09
    
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

    def setSize(self, h_w_size):
        self.c2 = {'x' : (self.c1['x'] + h_w_size[1]), 'y' : (self.c1['y'] + h_w_size[0])}

    def turn(self):
        self.c2['x'], self.c2['y'] = self.c1['x'] - self.c1['y'] + self.c2['y'], self.c1['y'] - self.c1['x'] + self.c2['x']
        self.r = 1/self.r

    def getSize(self):
        return (self.c2['y'] - self.c1['y'], self.c2['x'] - self.c1['x'])

    def height(self):
        return self.c2['y']-self.c1['y']
    def width(self):
        return self.c2['x']-self.c1['x']

    def S(self):
        return (self.c2['x']-self.c1['x']) * (self.c2['y']-self.c1['y'])

    def intersects(self, rect):
        xx1, yy1, xx2, yy2 = self.get_coord_list()
        x1, y1, x2, y2 = rect.get_coord_list()
        dx = np.minimum(x2, xx2) - np.maximum(x1, xx1) + 1
        dy = np.minimum(y2, yy2) - np.maximum(y1, yy1) + 1
        
        intersect = (dx > 0) & (dy > 0)
        return not (~intersect)

    def moveToOrigin(self):
        h, w = self.getSize()
        self.c1 = {'x': 0, 'y': 0}
        self.c2 = {'x': w, 'y': h}

# нужно для fcnr недописанного
class Level():
    def __init__(self, b : int, h : int, f : int =0, w : int =0):
        self.bottom = b
        self.height = h
        self.floor = f
        self.initW = w
        self.ceiling = 0

    def put(self, rect : Rect, H, W, f : bool = True, leftJustified : bool = True) -> Rect:
        newRect : Rect
 
        y = 0
        # по хорошему надо проверить работу r и {h, w}
        if f:
            if leftJustified:
                newRect = Rect(rect.r)
                newRect.setSize((rect.height(), rect.width()))
                y = H-(self.bottom + rect.height() + 1)
                newRect.move((self.floor, y))
            else:
                # 'ceiling' is used for right-justified rectangles packed on the floor
                newRect = Rect(1/rect.r)
                newRect.setSize((rect.width(), rect.height()))
                y = H-(self.bottom + rect.height() + 1)
                newRect.move((W-(self.ceiling + rect.width()), y))
                self.ceiling += rect.width()
            
            self.floor += rect.width()
        else:
            newRect = Rect(1/rect.r)
            newRect.setSize((rect.width(), rect.height()))
            y = H-(self.bottom + rect.height() + 1)
            newRect.move((W-(self.ceiling + rect.width()), y))
            self.ceiling += rect.width()
    
        if y >= 0 and y < H:
            return newRect
        return None

    def ceilingFeasible(self, rect : Rect, H, W, existing : list) -> bool:
        testRect : Rect
        testRect = Rect(1/rect.r)
        testRect.setSize((rect.width(), rect.height()))
        testRect.move((W-(self.ceiling + rect.width()), H-(self.bottom + rect.height() + 1)))

        intersected = False
        for i in range(len(existing)):
            if (testRect.intersects(existing[i])):
                intersected = True
                break
        
        fit : bool = rect.width() <= (W - self.ceiling - self.initW)
        return fit and not intersected

    def floorFeasible(self, rect : Rect, W : int) -> bool:
        return rect.width() <= (W - self.floor)

    def getSpace(self, W : int, f : bool=True) -> bool:
        if f:
            return W - self.floor
        else:
            return W - self.ceiling - self.initW


def get_cell(cols, rows, i, j, H, W):
    ''' считает размеры выбранной клетки '''
    c_h, c_w = (0, 0)
    if i == len(cols)-1:
        c_w = W - cols[i]
    else:
        c_w = cols[i+1] - cols[i]
    
    if j == len(rows)-1:
        c_h = H - rows[j]
    else:
        c_h = rows[j+1] - rows[j]

    return c_h, c_w


# актуальный вариант - писал сам с нуля
# работает медленнее classic - поэтому не использую
def packBurke(rects_ : list, fieldSize):
    '''
        по сути играем в тетрис
        уже лень комментировать более подробно
        суть алгоритма можно посмотреть задесь - https://habr.com/ru/articles/136225/
    '''
    rects = copy.deepcopy(rects_)
    for i in range(len(rects)):
        rects[i].moveToOrigin()

    positions = []
    real_indexes = []

    H, W = fieldSize
    hs, ws = zip(*[rect.getSize() for rect in rects])
    sorted_sides = sorted(list(enumerate(hs)) + list(enumerate(ws)), key=lambda x: x[1])
    ss = list(map(lambda x : x[1], sorted_sides))

    if sorted_sides[-1][1] > max(W, H):
        return None, None, True

    heights = [0 for _ in range(W)]
    while sorted_sides:
        # пока так. потом можно будет соптимизировать
        height, ind = heights[0], 0
        for i, h in enumerate(heights):
            if h < height:
                ind = i
                height = h
        h = 0
        # для выбранной высоты пытаемся вставить

        i = ind
        while i < W and heights[i] <= height:
            i += 1
        
        j = ind
        while j > -1 and heights[j] <= height:
            j -= 1

        space = i-j-1

        # мы нашли границы свободного пространства

        r_ind = bisect.bisect_left(ss, space)
        if r_ind < len(ss) and r_ind>0 and ss[r_ind] > space:
            r_ind = bisect.bisect_left(ss, ss[r_ind-1])

        # включительно
        l_bound, r_bound = (0, 0)
        pos = None
        real_ind = None
        if r_ind == 0 and sorted_sides[0][1] > space:
            # у нас нет достаточно узкого прямоугольника
            l_bound, r_bound = (j+1, i-1)
            
            r_b_height, l_b_height = None, None
            if i >= W:
                r_b_height, l_b_height = heights[j], heights[j]
            elif j < 0:
                l_b_height, r_b_height = heights[i], heights[i]
            else:
                l_b_height, r_b_height = heights[j], heights[i]
                

            new_h = min(l_b_height, r_b_height)
            
            h = new_h-height
        else:
            if r_ind == len(sorted_sides):
                r_ind = len(sorted_sides)-1
            
            r_b_height, l_b_height = (0, 0)
            if i < W:
                r_b_height = heights[i]
            if j > -1:
                l_b_height = heights[j]
            
            real_ind, width = sorted_sides[r_ind]

            # манипуляции с массивами прямоугольников
            h_, w = rects[real_ind].getSize()
            if w != width:
                rects[real_ind].setSize((w, h_))
                w, h_ = h_, w
            sorted_sides.pop(r_ind)
            ss.pop(r_ind)

            # ищем и удаляем другую сторону
            x = bisect.bisect_left(ss, h_)
            while sorted_sides[x][0] != real_ind:
                x += 1
            sorted_sides.pop(x)
            ss.pop(x)

            if r_b_height > l_b_height:
                # индекс для заливки
                l_bound = j+1
                r_bound = j+width
                pos = (j+1, height)
            else:
                # индекс для заливки
                r_bound = i-1
                l_bound = i-width
                pos = (i-width, height)
            h = h_

        heights[l_bound: r_bound+1] = [height+h for _ in range(l_bound, r_bound+1)]
        if pos:
            positions.append(pos)
            real_indexes.append(real_ind)
            rects[real_ind].move(pos)

    positions = [positions[ind] for ind in real_indexes]
    return rects, positions, False

def check_packed(packed, H, W) -> bool:
    '''
        возвращает True, если нашёл ошибку
    '''
    for rect in packed:
        coords = rect.get_coord_list()
        if coords[0] < 0 or coords[2] < coords[0] or coords[2] >= W:
            return False
        if coords[1] < 0 or coords[3] < coords[1] or coords[3] >= H:
            return True

    return False


def FCNR(rects : list, H, W) -> list :
    flag = "up"
    if H < W:
        flag = "right"
        H, W = W, H

    unpacked : list = copy.deepcopy(rects)
    unpacked.sort(key=(lambda x : x.height()))
 
    levels = []
    level = Level(0, unpacked[0].height(), 0, unpacked[0].width())
    packed = []
 
    packed.append(level.put(unpacked[0], H, W))
    levels.append(level)
 
    for i in range(1, len(unpacked)): # (int i = 1; i < unpacked.size(); i++) {
        found = -1
        minA = W
        for j in range(len(levels)): # (int j = 0; j < levels.size(); j++) {
            if levels[j].floorFeasible(unpacked[i], W):
                if levels[j].getSpace(W) < minA:
                    found = j
                    minA = levels[j].getSpace(W)
        
        if found > -1: # floor-pack on existing level
            packed.append(levels[found].put(unpacked[i], H, W))
        else:
            found = -1
            minA = W
            for j in range(len(levels)): # (int j = 0; j < levels.size(); j++) {
                if levels[j].ceilingFeasible(unpacked[i], H, W, packed):
                    if levels[j].getSpace(W, False) < minA:
                        found = j
                        minA = levels[j].getSpace(W, False)
            
            if found > -1: # ceiling-pack on existing level
                packed.append(levels[found].put(unpacked[i], H, W, False))
            else: # a new level
                newLevel = Level(levels[-1].bottom + levels[-1].height, unpacked[i].height(), 0, unpacked[i].width())
                packed.append(newLevel.put(unpacked[i], H, W))
                levels.append(newLevel)
        
        if packed[-1] is None:
            return None, True

    err = check_packed(packed, H, W)
    if not err:
        return packed, False
    else:
        return None, True


def append_to_field(rect : Rect, field, cols, rows, H_, W_):
    '''
        классическая вставка
        ищет место для вставки в поле и если находит - вставляет
        суть алгоритма брал отсюда - https://www.codeproject.com/Articles/210979/Fast-optimizing-rectangle-packing-algorithm-for-bu
        но вообще, если бы и сам писал, то наверное так же сделал - максимально наивная вещь
    '''
    h, w = rect.getSize()
    l_r, l_c = len(rows), len(cols)

    for i, col in enumerate(cols):
        for j, row in enumerate(rows):
            # если клетка свободна
            if col < W_ and row < H_ and not (row, col) in field:

                # собираем достаточный размер по y
                k = j
                H = 0
                while k < l_r and not (rows[k],col) in field:
                    # считаем размеры текущей клетки
                    c_h, c_w = get_cell(cols, rows, i, k, H_, W_)

                    H += c_h
                    k += 1
                    if H >= h:
                        break
                else:
                    if k == l_r:
                        H = H_ - row
                    # если не получилось собрать высоту - смотрим другие ячейки
                    if H < h:
                        continue

                # собираем ширину - x
                l = i
                W = 0
                # проверяем все в выбранном диапазоне rows
                while l < l_c and not any((rows[t], cols[l]) in field for t in range(j, min(k, l_r))):
                    # считаем размеры свободной клетки
                    c_h, c_w = get_cell(cols, rows, l, j, H, W_)
                    W += c_w
                    l += 1
                    # если достаточно - выходим
                    if W >= w:
                        break
                else:
                    if l == l_c:
                        W = W_ - col
                    # если не хватило
                    if W < w:
                        continue

                # делаем разрез по rows
                if (col + w) not in cols and (col + w) < W_:
                    bisect.insort(cols, col + w)
                    for ind, row_ in enumerate(rows):
                        if (row_, cols[l-1]) in field:
                            field.add((row_, cols[l]))
                # делаем разрез по столбцам
                if (row + h) not in rows and (row + h) < H_:
                    bisect.insort(rows, row + h)
                    for ind, col_ in enumerate(cols):
                        if (rows[k-1], col_) in field:
                            field.add((rows[k], cols[ind]))

                #добавляем поные заполненные клетки
                for ind1 in range(j, k):
                    for ind2 in range(i, l):
                        field.add((rows[ind1], cols[ind2]))
                
                # перемещаем прямоугольник на выбранную позицию
                rect.move((col, row))
                return rect, False

    return None, True

def convert_to_clasic(pos, rects, fieldSize=(100, 100)):
    '''
        конвертируем результат поля бёрка для работы классического алгоритма
    '''
    H, W = fieldSize
    field = set([(H, 0), (0, W), (H, W)])
    rects = []
    cols = set([0, W])
    rows = set([0, H])

    for rect in rects:
        c1, c2 = rect.c1, rect.c2
        x1, y1, x2, y2 = c1['x'], c1['y'], c2['x'], c2['y']
        cols.add(x1)
        cols.add(x2)
        rows.add(y1)
        rows.add(y2)

    rows = sorted(list(rows))
    cols = sorted(list(cols))

    for rect in rects:
        c1, c2 = rect.c1, rect.c2
        x1, y1, x2, y2 = c1['x'], c1['y'], c2['x'], c2['y']
        i1 = bisect.bisect_left(rows, x1)
        i2 = bisect.bisect_left(rows, x2)
        j1 = bisect.bisect_left(cols, y1)
        j2 = bisect.bisect_left(cols, y2)

        field = field.union(itertools.product(rows[i1:i2], cols[j1:j2]))
    field = field.union(itertools.product(rows, [0 for _ in range(H)]))
    field = field.union(itertools.product(cols, [0 for _ in range(W)]))

    return field, cols, rows


def generateSizes(r : float, H, W):
    '''
        генерирует все возможные комбинации сторон, удовленворяющие ограничениям
        работает за O(n/2), где n ~ H
    '''

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


def tryCombo(rs, size_combo, H, W, algo="classic"):
    '''
        пытается запихнуть прямоугольники переданных размеров в поле по указанному алгоритму
    '''

    # храним занятые угловые ячейки (поле в алгоритме classic делится на ячейки, имеющие статус занято/не занято, 
    # и чтобы не хранить матрицу поля достаточно угловых клеток тих ячеек)
    field = set([(H, 0), (0, W), (H, W)])


    # храним отсечки - границы ячеек
    cols = [0, W]
    rows = [0, H]

    # массов повёрнутых и передвинутых прямоугольников
    rects = []
    # инициализируем прямоугольники для вставки
    for i, combo in enumerate(size_combo):
        rect = Rect(rs[i])
        rect.setSize(combo)
        rects.append(rect)


    if algo == "classic":
        # сортируем по высоте для лучшего score
        rects.sort(key=(lambda x: x.height()), reverse=True)
        
        # по очереди вставляем все прямоугольники
        for i in range(len(rects)):
            err = True
            rect = rects[i]
            rr, err = append_to_field(rect, field, cols, rows, H, W)
            
            # если не влезло одним боком - может влезет другим
            if err:
                rect.turn()
                rr, err = append_to_field(rect, field, cols, rows, H, W)
            rects[i] = rr

            if err == True:
                return None, True
    elif algo == "burke":
        '''
            пихаем бёрком как получится, а потом невпихнутое довпихиваем классикой
            работает дольше классики, качество +- то же, если не хуже
        '''

        rects1, positions, err = packBurke(rects, (H, W))
        if err == True:
            return None, True
        
        bad_rects = list(filter(lambda rect : rect.c2['y'] > H, rects1))
        good_rects = list(filter(lambda rect : rect.c2['y'] <= H, rects1))
        field, cols, rows = convert_to_clasic(positions, good_rects, (H, W))

        for i, rect in enumerate(bad_rects):
            err = True
            rect = bad_rects[i]
            rr, err = append_to_field(rect, field, cols, rows, H, W)
            if err:
                rect.turn()
                rr, err = append_to_field(rect, field, cols, rows, H, W)
            bad_rects[i] = rr

            if err == True:
                return None, True

        rects = good_rects + bad_rects
            
    elif algo == "FCNR":
        # не работает
        rects, err = FCNR(rects, H, W)
        if err == True:
            return None, True

    line = []
    placements = []

    # для каждого r находим его прямоугольник и добавляем его координаты в результат
    # бин поиск не сильно ускорил дело
    for r in rs:
        for i, rect in enumerate(rects):
            if abs(r - rect.r) < 0.09 or abs(r - 1/rect.r) < 0.09:
                line += rect.get_coord_list()
                rects.pop(i)
                break

    # если не все прямоугольники получилось распределить
    if len(rects) != 0:
        print("!!! there is some bad rect !!!")
        for rect in rects:
            print(rect)
        raise "rect determination problem"
    
    return line, False


# пробовать несколько выриантов - слишком дорого и не выгодно. возвращаем первый подошедший
def findOptFullRand(rs, sizes, size_combo, H, W, selfS):
    '''
        рекурсивная функция поиска оптимального решения 
        по сути мы обходим дерево комбинаций размеров
        понятно, что это очень долго, поэтому после долгих 
        дум я всё же решил выходит при первом же встреченном подходящем решении
        + здесь можно выбирать алгоритм заполнения. на выбор classic, burke или fcnr (не доделан)
        burke чуть лучше classic на task2, но куда медленнее, поэтому оставил classic
    '''

    # если спустились до листа и собрали комбо
    if sizes == []:
        positions, err = tryCombo(rs, size_combo, H, W, algo="classic")
        if err == False:
            return positions, selfS, err
        else:
            return None, None, err

    best_combo_positions = None
    maxS = 0
    
    # пробегаемся по всем размерам
    for ind, size in enumerate(sizes[0]):
        # если мы берём слишком большой размер - даже не пробуем подставлять
        if size[0]*size[1] > H*W-selfS:
            continue

        size_combo.append(size)
        positions, S, err = findOptFullRand(rs, sizes[1:], size_combo, H, W, selfS+size_combo[-1][0]*size_combo[-1][1])
        size_combo.pop(-1)
        
        if not err:
            if S > maxS:
                best_combo_positions = positions
                maxS = S
                return best_combo_positions, maxS, False

    # когда закончились размеры
    if best_combo_positions:
        return best_combo_positions, maxS, False
    else:
        return None, None, True


def unshuffle(pos, sh_r, order):
    '''
        восстанавливает изначальный порядок
        O(n), где n - количество прямоугольников
    '''
    undone_pos = pos.copy()
    for i, s in enumerate(sh_r):
        ind = order[s][-1]
        order[s].pop(-1)
        undone_pos[ind*4 : (ind+1)*4] = pos[i*4 : (i+1)*4]

    return undone_pos

import random

# использую это - всё пологается на рандомный выбор набора размеров
def solveCaseFullRand(case) -> np.array:
    # print(case)
    H, W = int(case[0]), int(case[1])
    rs = case[2:]

    # генерируем все возможные размеры для rects
    sizes = []
    for r in rs:
        sizes.append(generateSizes(r, H, W))

    Smax = 0
    position = None
    seed(42)
    # пробовал менят отношение, но оставил как есть по итогу
    x1 = [(line[:max(1, (len(line)*8)//10)], 1) for line in sizes]
    x2 = [[line[-1]] for line in sizes]

    # поменял здесь, чтобы по времени проходило
    # нужно знать результаты пробных запусков, а у меня на руках их нет :-(
    # ладно, оставлю как есть тое пока
    for _ in range(350):
        # делаем рандомное подмножество, не забывая про минимум, чтоб точно нашлось решение
        rand_sizes = [random.sample(x1[0], x1[1]) + x2 for x1, x2 in zip(x1, x2)]

        for _ in range(2):
            sh_r_sizes = list(zip(rs, rand_sizes))
            order = defaultdict(list)
            for i, s in enumerate(sh_r_sizes):
                order[s[0]].append(i)
            
            # sh_r_sizes = r_sizes.copy()

            # пробуем 2 варианта : перемешку и сортированный
            if i % 2 == 0:
                shuffle(sh_r_sizes)
            elif i % 2 == 1:
                # sh_r_sizes.sort()
                sh_r_sizes.sort(key = (lambda x: x[0]))

            sh_r = [r for r, _ in sh_r_sizes]
            sh_sizes = [sizes for _, sizes in sh_r_sizes]

            pos, S, err = findOptFullRand(sh_r, sh_sizes, [], H, W, 0)

            if not err and S > Smax:
                position = unshuffle(pos, sh_r, copy.deepcopy(order))
                Smax = S
            if err:
                raise "error"

    return position

@benchmark
def solution(task) -> np.array:
    data_frame = []

    # немного параллелизма в студию ))
    with multiprocessing.Pool(2) as pool:
        data_frame = pool.map(wrapped_func, task)
    
    return np.asarray(data_frame, dtype=int)


import multiprocessing

def main():
    task = np.genfromtxt(sys.argv[1] , delimiter=",", skip_header=1) # [:10, :]
    print("shape: ", task.shape)

    sol = solution(task)
    sol = np.asarray(sol, dtype=str)

    # запаковываем и сохраняем в виде csv
    header = (', '.join([f'X{i+1}min, Y{i+1}min, X{i+1}max, Y{i+1}max' for i in range(len(sol[0]) // 4)])).split(', ')
    sol = np.insert(sol, 0, np.asarray(header, dtype=str), axis=0)
    np.savetxt("solution.csv", sol, delimiter=",", fmt="%s")

if __name__ == '__main__':
    main()