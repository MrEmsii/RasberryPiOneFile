# Author: Emsii 
# Date: 01.03.2024
# https://github.com/EmsiiDiss

##InProgrogress!!!


import sqlite3
import datetime
import os

def connectBase(path, file):
    connect = sqlite3.connect(str(path) + str(file))
    return connect


def create_table(cursor, table_name, columns):
    column_definitions = ', '.join([f"{col} VARCHAR(250) NOT NULL" for col in columns])
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY ASC, {column_definitions})"
    cursor.execute(create_table_query)

def collect(connect, tab, id, column):
    cur = connect.cursor()
    cur.execute('SELECT * FROM %s WHERE id=?;' % tab, (str(id)))
    for row in cur.fetchall():
        return row[column]

def table_maker(connect, columns, table_name):
    cur = connect.cursor()
    create_table(cur, table_name, columns)
    closeBase(connect, "yes")

def updateBase(connect, table_name, data_list, place):
    cursor = connect.cursor()
    update_query = f"UPDATE {table_name} SET {place} = ? WHERE id = ?"
    for data_tuple in data_list:
        cursor.execute(update_query, data_tuple)    


def insertBase(connect, table_name, data_list, place):
    cursor = connect.cursor()
    num_columns = len(data_list[0])
    placeholders = ', '.join(['?' for _ in range(num_columns)])
    insert_query = f"INSERT INTO {table_name} VALUES ({place}{placeholders})"
    for data_tuple in data_list:
        cursor.execute(insert_query, data_tuple)

def closeBase(connect, save):
    if save == "yes":
        connect.commit()
    connect.close()	