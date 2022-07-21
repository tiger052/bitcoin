from Util.const import *

def createLog():
    path = "Log/output.log"
    try:
        with open(path, 'w') as file:
            file.write("")
    except Exception as e:
        print(e)


def clearLog():
    path = "Log/output.log"
    try:
        txt = loadLog()
        with open(path, 'w') as file:
            file.write("")
    except Exception as e:
        print(e)

def saveLog(text):
    path = "Log/output.log"
    try:
        txt = loadLog()
        if txt is None:
            print("File is None! - Create Log File")
            createLog()
            return
        print(text)
        if len(txt) == 0:
            with open(path, 'w') as file:
                file.write("{}".format(text))
        else:
            with open(path, 'w') as file:
                file.write("{}{}".format(txt, "\n" + text))

    except Exception as e:
        print(e)

def loadLog():
    path = "Log/output.log"
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
    #print(len(data))
    pass