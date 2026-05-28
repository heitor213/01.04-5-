import random
import tkinter

okno = tkinter.Tk()

ot = tkinter.Label(okno, text="от:")
ot.pack()
pole_ot = tkinter.Entry(okno)
pole_ot.pack()

do = tkinter.Label(okno, text="до:")
do.pack()
pole_do = tkinter.Entry(okno)
pole_do.pack()

knopka = tkinter.Button(okno, text="начать")
knopka.pack()

rezultat = tkinter.Label(okno, text="")
rezultat.pack()

spisok = []

def nachati():
    x = int(pole_ot.get())
    y = int(pole_do.get())
    for i in range(x, y+1):
        spisok.append(i)
    rezultat.config(text="готово, жмякай на entor")

knopka.config(command=nachati)

def nagatie(event):
    if len(spisok) == 0:
        rezultat.config(text="Числа закончились")
        return
    chislo = random.choice(spisok)
    spisok.remove(chislo)
    rezultat.config(text=chislo)

okno.bind("<Return>", nagatie)

okno.mainloop()