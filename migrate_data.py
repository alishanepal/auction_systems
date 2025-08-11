import sqlite3
import os

OLD_DB = 'instance/auction.db'
NEW_DB = 'instance/auction_clean.db'

if not os.path.exists(OLD_DB):
    print(f"Old DB not found at {OLD_DB}")
    raise SystemExit(1)
if not os.path.exists(NEW_DB):
    print(f"New DB not found at {NEW_DB}")
    raise SystemExit(1)

conn = sqlite3.connect(NEW_DB)
cur = conn.cursor()

print('Attaching old database...')
cur.execute("ATTACH DATABASE ? AS old", (OLD_DB,))

# Helper to insert with explicit id preservation

def copy_table_with_ids(table, columns):
    cols_csv = ",".join(columns)
    sql = f"INSERT OR IGNORE INTO {table} ({cols_csv}) SELECT {cols_csv} FROM old.{table}"
    print(f"Copying {table}...")
    cur.execute(sql)

try:
    # Copy base/plural tables preserving IDs
    copy_table_with_ids('users', [
        'id','username','email','password_hash','role','status','created_at'
    ])
    copy_table_with_ids('categories', ['id','name'])
    copy_table_with_ids('subcategories', ['id','name','category_id'])
    copy_table_with_ids('products', [
        'id','name','starting_bid','reserve_price','description','keywords',
        'minimum_interval','category_id','subcategory_id','seller_id','image_url','created_at'
    ])
    copy_table_with_ids('auctions', ['id','product_id','start_date','end_date','type','created_at'])
    copy_table_with_ids('bids', ['id','auction_id','bidder_id','bid_amount','bid_time'])
    copy_table_with_ids('auction_results', ['id','auction_id','winner_id','winning_bid','ended_at'])

    # Copy search_history if present in old
    cur.execute("SELECT name FROM old.sqlite_master WHERE type='table' AND name='search_history'")
    if cur.fetchone():
        print('Copying search_history...')
        cur.execute(
            """
            INSERT OR IGNORE INTO search_history (id, user_id, query, search_type, timestamp)
            SELECT id, user_id, query, search_type, timestamp FROM old.search_history
            """
        )

    # Build aggregated bid_history from old bids
    print('Aggregating bid_history from bids...')
    cur.execute("DELETE FROM bid_history")
    cur.execute(
        """
        INSERT INTO bid_history (
            user_id, product_id, category_id, subcategory_id, seller_id, bid_count, last_bid_time
        )
        SELECT 
            b.bidder_id AS user_id,
            a.product_id AS product_id,
            p.category_id,
            p.subcategory_id,
            p.seller_id,
            COUNT(*) AS bid_count,
            MAX(b.bid_time) AS last_bid_time
        FROM old.bids b
        JOIN old.auctions a ON a.id = b.auction_id
        JOIN old.products p ON p.id = a.product_id
        GROUP BY b.bidder_id, a.product_id
        """
    )

    conn.commit()
    # Show row counts
    for table in ['users','categories','subcategories','products','auctions','bids','auction_results','search_history','bid_history']:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        count = cur.fetchone()[0]
        print(f"{table}: {count}")

    print('Data migration complete.')
except Exception as e:
    conn.rollback()
    raise
finally:
    cur.execute('DETACH DATABASE old')
    conn.close()
