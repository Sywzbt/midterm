import sqlite3
from typing import Optional
import sys

DB_NAME = "bookstore.db"
DATE_FORMAT_LENGTH = 10


def initialize_database() -> None:
    """初始化資料庫與資料表，若不存在則建立並插入初始資料"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.executescript(
            """
        CREATE TABLE IF NOT EXISTS member (
            mid TEXT PRIMARY KEY,
            mname TEXT NOT NULL,
            mphone TEXT NOT NULL,
            memail TEXT
        );

        CREATE TABLE IF NOT EXISTS book (
            bid TEXT PRIMARY KEY,
            btitle TEXT NOT NULL,
            bprice INTEGER NOT NULL,
            bstock INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sale (
            sid INTEGER PRIMARY KEY AUTOINCREMENT,
            sdate TEXT NOT NULL,
            mid TEXT NOT NULL,
            bid TEXT NOT NULL,
            sqty INTEGER NOT NULL,
            sdiscount INTEGER NOT NULL,
            stotal INTEGER NOT NULL
        );

        INSERT OR IGNORE INTO member VALUES 
        ('M001', 'Alice', '0912-345678', 'alice@example.com'),
        ('M002', 'Bob', '0923-456789', 'bob@example.com'),
        ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

        INSERT OR IGNORE INTO book VALUES 
        ('B001', 'Python Programming', 600, 50),
        ('B002', 'Data Science Basics', 800, 30),
        ('B003', 'Machine Learning Guide', 1200, 20);

        INSERT OR IGNORE INTO sale (sid, sdate, mid, bid, sqty, sdiscount, stotal) VALUES 
        (1, '2024-01-15', 'M001', 'B001', 2, 100, 1100),
        (2, '2024-01-16', 'M002', 'B002', 1, 50, 750),
        (3, '2024-01-17', 'M001', 'B003', 3, 200, 3400),
        (4, '2024-01-18', 'M003', 'B001', 1, 0, 600);
        """
        )
        conn.commit()


def input_int(
    prompt: str, positive_only: bool = False, allow_zero: bool = False
) -> int:
    """取得整數輸入並驗證"""
    while True:
        try:
            value = int(input(prompt))
            if positive_only and value <= 0:
                print("=> 錯誤：數值必須為正整數")
                continue
            if not allow_zero and value < 0:
                print("=> 錯誤：數值不能為負數")
                continue
            return value
        except ValueError:
            print("=> 錯誤：請輸入有效的整數")


def add_sale() -> None:
    """新增銷售記錄"""
    sdate = input("請輸入銷售日期 (YYYY-MM-DD)：").strip()
    if len(sdate) != DATE_FORMAT_LENGTH or sdate.count("-") != 2:
        print("=> 錯誤：日期格式錯誤")
        return

    mid = input("請輸入會員編號：").strip()
    bid = input("請輸入書籍編號：").strip()

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM member WHERE mid = ?", (mid,))
        member = cursor.fetchone()
        cursor.execute("SELECT * FROM book WHERE bid = ?", (bid,))
        book = cursor.fetchone()

        if not member or not book:
            print("=> 錯誤：會員編號或書籍編號無效")
            return

        sqty = input_int("請輸入購買數量：", positive_only=True)
        if book["bstock"] < sqty:
            print(f"=> 錯誤：書籍庫存不足 (現有庫存: {book['bstock']})")
            return

        sdiscount = input_int("請輸入折扣金額：", allow_zero=True)
        stotal = (book["bprice"] * sqty) - sdiscount

        try:
            cursor.execute("BEGIN")
            cursor.execute(
                """
                INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) 
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (sdate, mid, bid, sqty, sdiscount, stotal),
            )
            cursor.execute(
                "UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid)
            )
            conn.commit()
            print(f"=> 銷售記錄已新增！(銷售總額: {stotal:,})")
        except sqlite3.Error:
            conn.rollback()
            print("=> 錯誤：新增失敗，資料庫操作異常")


def show_report() -> None:
    """顯示銷售報表"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
        """
        )
        rows = cursor.fetchall()

    for i, row in enumerate(rows, 1):
        print(f"\n銷售 #{i}")
        print(f"銷售編號: {row['sid']}")
        print(f"銷售日期: {row['sdate']}")
        print(f"會員姓名: {row['mname']}")
        print(f"書籍標題: {row['btitle']}")
        print("--------------------------------------------------")
        print("單價\t數量\t折扣\t小計")
        print("--------------------------------------------------")
        print(f"{row['bprice']}\t{row['sqty']}\t{row['sdiscount']}\t{row['stotal']:,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {row['stotal']:,}")
        print("==================================================")


def list_sales() -> list[sqlite3.Row]:
    """列出銷售記錄，回傳記錄清單"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
        SELECT s.sid, m.mname, s.sdate
        FROM sale s
        JOIN member m ON s.mid = m.mid
        ORDER BY s.sid
        """
        )
        return cursor.fetchall()


def update_sale() -> None:
    """更新銷售記錄的折扣金額"""
    sales = list_sales()
    print("\n======== 銷售記錄列表 ========")
    for i, s in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {s['sid']} - 會員: {s['mname']} - 日期: {s['sdate']}")
    print("================================")

    choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice:
        return
    try:
        index = int(choice) - 1
        if index < 0 or index >= len(sales):
            raise ValueError
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return

    sid = sales[index]["sid"]
    new_discount = input_int("請輸入新的折扣金額：", allow_zero=True)

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT bid, sqty FROM sale WHERE sid = ?", (sid,))
        sale = cursor.fetchone()
        cursor.execute("SELECT bprice FROM book WHERE bid = ?", (sale["bid"],))
        price = cursor.fetchone()["bprice"]
        new_total = (price * sale["sqty"]) - new_discount

        try:
            cursor.execute(
                """
                UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?
            """,
                (new_discount, new_total, sid),
            )
            conn.commit()
            print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")
        except sqlite3.Error:
            conn.rollback()
            print("=> 錯誤：更新失敗")


def delete_sale() -> None:
    """刪除銷售記錄"""
    sales = list_sales()
    print("\n======== 銷售記錄列表 ========")
    for i, s in enumerate(sales, 1):
        print(f"{i}. 銷售編號: {s['sid']} - 會員: {s['mname']} - 日期: {s['sdate']}")
    print("================================")

    choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")
    if not choice:
        return
    try:
        index = int(choice) - 1
        if index < 0 or index >= len(sales):
            raise ValueError
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return

    sid = sales[index]["sid"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM sale WHERE sid = ?", (sid,))
            conn.commit()
            print(f"=> 銷售編號 {sid} 已刪除")
        except sqlite3.Error:
            conn.rollback()
            print("=> 錯誤：刪除失敗")


def main() -> None:
    """主選單"""
    initialize_database()
    while True:
        print(
            """
***************選單***************
1. 新增銷售記錄
2. 顯示銷售報表
3. 更新銷售記錄
4. 刪除銷售記錄
5. 離開
**********************************
"""
        )
        choice = input("請選擇操作項目(輸入後請按 Enter)：").strip()
        if not choice:
            continue
        if choice == "1":
            add_sale()
        elif choice == "2":
            show_report()
        elif choice == "3":
            update_sale()
        elif choice == "4":
            delete_sale()
        elif choice == "5":
            print("=> 離開程式")
            sys.exit()
        else:
            print("=> 請輸入有效的選項（1-5）")


if __name__ == "__main__":
    main()
