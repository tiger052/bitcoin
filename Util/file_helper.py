from Util.const import *

def createLog():
    path = logFileName
    try:
        with open(path, 'w') as file:
            file.write("")
    except Exception as e:
        print(e)


def clearLog():
    path = logFileName
    try:
        txt = loadLog()
        with open(path, 'w') as file:
            file.write("")
    except Exception as e:
        print(e)

def saveLog(text):
    path = logFileName
    try:
        txt = loadLog()
        if txt is None:
            print("none")
            pass
        if len(txt) == 0:
            with open(path, 'w') as file:
                file.write("{}".format(text))
        else:
            with open(path, 'w') as file:
                file.write("{}{}".format(txt, "\n" + text))

    except Exception as e:
        print(e)

def loadLog():
    path = logFileName
    try:
        with open(path, 'r') as file:
            doc = file.read()
            return doc
    except Exception as e:
        print(e)
        return None

if __name__ == "__main__":
    #createLog()
    #pass
    #clearLog()
    saveLog("test")
    data = loadLog()
    print(len(data))
    pass