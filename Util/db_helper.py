# db_helper.py #
import sqlite3
import pandas as pd

def check_table_exist(db_name, table_name):
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        cur = con.cursor()
        sql = "SELECT name FROM sqlite_master WHERE type='table' and name =:table_name"
        cur.execute(sql, {"table_name":table_name})

        if len(cur.fetchall()) > 0:
            return True
        else:
            return False

def clear_table_db(db_name, table_name):
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        cur = con.cursor()
        sql = "delete from {}".format(table_name)        # 저장된 데이터의 가장 최근 일자 조회
        cur.execute(sql)
        return cur

def insert_df_to_db(db_name, table_name, df, option="replace"):
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        df.to_sql(table_name, con, if_exists=option)

def execute_sql(db_name, sql, param={}):
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        cur = con.cursor()
        cur.execute(sql, param)
        return cur

def execute_sql_to_dataframe(db_name, sql):
    with sqlite3.connect('{}.db'.format(db_name)) as con:
        df = pd.read_sql_query(sql, con)
        return df