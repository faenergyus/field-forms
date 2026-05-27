"""Migrate well_file_summary.xlsx 9 sheets to SQL Server (sf\\sqldev Ops_Reporting).

All tables prefixed wbd_ so they group together in SSMS object explorer.
Drops + recreates on each run.
"""
import openpyxl
import pyodbc

XLSX = r"C:\Users\RSwift\OneDrive - faenergyus\General\OPERATIONS\AI Projects\Well Info\well_file_summary.xlsx"

CONN_STR = r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=sf\sqldev;DATABASE=Ops_Reporting;Trusted_Connection=yes;TrustServerCertificate=yes;"

# Map xlsx sheet -> (sql table name, column DDL list, FK columns)
TABLES = [
    {
        "sheet": "wells",
        "table": "wbd_wells",
        "ddl": """CREATE TABLE dbo.wbd_wells (
            well_id INT NOT NULL PRIMARY KEY,
            well_name NVARCHAR(200) NULL,
            api NVARCHAR(20) NULL,
            source_folder NVARCHAR(50) NULL,
            county NVARCHAR(50) NULL,
            state NVARCHAR(10) NULL,
            field NVARCHAR(50) NULL,
            township NVARCHAR(20) NULL,
            [range] NVARCHAR(20) NULL,
            [section] NVARCHAR(30) NULL,
            location NVARCHAR(100) NULL,
            tsr NVARCHAR(30) NULL,
            formation NVARCHAR(200) NULL,
            lease_no NVARCHAR(30) NULL,
            lease_type NVARCHAR(30) NULL,
            spud_date NVARCHAR(30) NULL,
            completion_date NVARCHAR(30) NULL,
            kb NVARCHAR(20) NULL,
            df NVARCHAR(20) NULL,
            gl NVARCHAR(20) NULL,
            ogrid NVARCHAR(20) NULL
        )""",
    },
    {
        "sheet": "wbd_versions",
        "table": "wbd_versions",
        "ddl": """CREATE TABLE dbo.wbd_versions (
            wbd_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_date NVARCHAR(20) NULL,
            status NVARCHAR(50) NULL,
            source_file NVARCHAR(500) NULL,
            file_format NVARCHAR(20) NULL,
            sheet_name NVARCHAR(50) NULL,
            td NVARCHAR(20) NULL,
            pbtd NVARCHAR(20) NULL,
            data_extracted BIT NULL
        )""",
    },
    {
        "sheet": "casing",
        "table": "wbd_casing",
        "ddl": """CREATE TABLE dbo.wbd_casing (
            casing_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            casing_type NVARCHAR(50) NULL,
            size NVARCHAR(100) NULL,
            weight NVARCHAR(100) NULL,
            grade NVARCHAR(100) NULL,
            set_depth NVARCHAR(100) NULL,
            hole_size NVARCHAR(100) NULL,
            cement_sacks NVARCHAR(200) NULL,
            toc NVARCHAR(100) NULL,
            circ_to_surface NVARCHAR(50) NULL,
            notes NVARCHAR(MAX) NULL
        )""",
    },
    {
        "sheet": "perforations",
        "table": "wbd_perforations",
        "ddl": """CREATE TABLE dbo.wbd_perforations (
            perf_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            top_depth NVARCHAR(50) NULL,
            bottom_depth NVARCHAR(50) NULL,
            spf NVARCHAR(20) NULL,
            zone NVARCHAR(200) NULL,
            perf_date NVARCHAR(50) NULL,
            is_squeezed BIT NULL,
            squeeze_date NVARCHAR(50) NULL,
            notes NVARCHAR(MAX) NULL
        )""",
    },
    {
        "sheet": "plugs",
        "table": "wbd_plugs",
        "ddl": """CREATE TABLE dbo.wbd_plugs (
            plug_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            plug_type NVARCHAR(100) NULL,
            depth NVARCHAR(50) NULL,
            toc NVARCHAR(100) NULL,
            cement_sacks NVARCHAR(50) NULL,
            notes NVARCHAR(MAX) NULL
        )""",
    },
    {
        "sheet": "fish",
        "table": "wbd_fish",
        "ddl": """CREATE TABLE dbo.wbd_fish (
            fish_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            description NVARCHAR(MAX) NULL,
            depth NVARCHAR(50) NULL,
            notes NVARCHAR(500) NULL
        )""",
    },
    {
        "sheet": "formation_tops",
        "table": "wbd_formation_tops",
        "ddl": """CREATE TABLE dbo.wbd_formation_tops (
            top_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            formation_name NVARCHAR(200) NULL,
            depth NVARCHAR(50) NULL
        )""",
    },
    {
        "sheet": "tubing",
        "table": "wbd_tubing",
        "ddl": """CREATE TABLE dbo.wbd_tubing (
            tubing_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            description NVARCHAR(MAX) NULL,
            depth NVARCHAR(50) NULL,
            joints NVARCHAR(50) NULL,
            notes NVARCHAR(500) NULL,
            size NVARCHAR(40) NULL
        )""",
    },
    {
        "sheet": "rods",
        "table": "wbd_rods",
        "ddl": """CREATE TABLE dbo.wbd_rods (
            rod_id INT NOT NULL PRIMARY KEY,
            well_id INT NULL,
            wbd_id INT NULL,
            description NVARCHAR(500) NULL,
            count NVARCHAR(50) NULL,
            length NVARCHAR(50) NULL,
            depth NVARCHAR(50) NULL,
            notes NVARCHAR(500) NULL
        )""",
    },
]

print("Connecting to sf\\sqldev Ops_Reporting...")
conn = pyodbc.connect(CONN_STR, autocommit=False)
cur = conn.cursor()
cur.fast_executemany = True

print("Loading xlsx...")
wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)

for cfg in TABLES:
    sheet = cfg["sheet"]
    table = cfg["table"]
    print(f"\n=== {sheet} -> dbo.{table} ===")

    # Drop + recreate
    cur.execute(f"IF OBJECT_ID('dbo.{table}', 'U') IS NOT NULL DROP TABLE dbo.{table}")
    cur.execute(cfg["ddl"])
    conn.commit()

    # Load rows
    ws = wb[sheet]
    rows_iter = ws.iter_rows(values_only=True)
    headers = list(next(rows_iter))
    cols = ", ".join(f"[{h}]" for h in headers)
    placeholders = ", ".join(["?"] * len(headers))
    insert_sql = f"INSERT INTO dbo.{table} ({cols}) VALUES ({placeholders})"

    batch = []
    for r in rows_iter:
        # Normalize: convert empty strings to None, truncate if too long is handled by SQL
        rec = []
        for v in r:
            if v == "" or v is None:
                rec.append(None)
            elif isinstance(v, bool):
                rec.append(1 if v else 0)
            else:
                rec.append(v)
        batch.append(tuple(rec))

    if batch:
        cur.executemany(insert_sql, batch)
        conn.commit()
    print(f"  Inserted {len(batch)} rows")

# Add helpful indexes for join performance
print("\nCreating indexes...")
for stmt in [
    "CREATE INDEX IX_wbd_versions_well ON dbo.wbd_versions(well_id) INCLUDE (data_extracted)",
    "CREATE INDEX IX_wbd_casing_wbd ON dbo.wbd_casing(wbd_id)",
    "CREATE INDEX IX_wbd_perforations_wbd ON dbo.wbd_perforations(wbd_id)",
    "CREATE INDEX IX_wbd_plugs_wbd ON dbo.wbd_plugs(wbd_id)",
    "CREATE INDEX IX_wbd_fish_wbd ON dbo.wbd_fish(wbd_id)",
    "CREATE INDEX IX_wbd_formation_tops_wbd ON dbo.wbd_formation_tops(wbd_id)",
    "CREATE INDEX IX_wbd_tubing_wbd ON dbo.wbd_tubing(wbd_id)",
    "CREATE INDEX IX_wbd_rods_wbd ON dbo.wbd_rods(wbd_id)",
    "CREATE INDEX IX_wbd_wells_api ON dbo.wbd_wells(api)",
]:
    try:
        cur.execute(stmt)
        conn.commit()
        print(f"  + {stmt.split(' ON ')[0].replace('CREATE INDEX ', '')}")
    except Exception as e:
        print(f"  ! {e}")

# Final summary
print("\n=== Final row counts ===")
for cfg in TABLES:
    cur.execute(f"SELECT COUNT(*) FROM dbo.{cfg['table']}")
    print(f"  dbo.{cfg['table']}: {cur.fetchone()[0]}")

conn.close()
print("\nDone.")
