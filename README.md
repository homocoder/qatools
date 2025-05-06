# qatools: ALMA Science Data Model Interaction Library

A Python library designed for interacting with ALMA Science Data Model (ASDM) datasets, primarily focusing on data access, manipulation, and conversion for quality assessment and analysis purposes.

This library provides tools to programmatically access ASDM table contents, both from XML metadata entities and associated binary data files, leveraging the ALMA Archive's metadata database (Oracle).

**Target Audience:** ALMA Staff, Astronomers, Data Analysts working directly with ALMA ASDM datasets.

## Key Features

- **ASDM Index Access:** Read and parse the main `ASDM.xml` index file to get an overview of the tables within an ASDM execution.
- **ASDM Table Reading:**
  - Fetch individual ASDM table data based on their UIDs from the ALMA metadata archive (Oracle).
  - Parse XML representations of ASDM tables into Python objects.
  - Handle tables stored as binary data by invoking helper scripts (requires AIDA environment).
- **Data Representation:**
  - Provides classes (`ASDMIndex`, `ASDMTable`) to represent ASDM components.
  - Includes a generic `aidaTable` class for representing tabular data, capable of being populated from ASDM objects or database queries.
- **Data Access Methods:** Offers methods to retrieve entire tables, specific rows, specific field values, or field names within an ASDM table.
- **Database Interaction:**
  - Connects to ALMA metadata Oracle database for fetching ASDM XML.
  - Connects to local PostgreSQL (`aidadb`) or in-memory SQLite (`ramdb`) databases.
  - Populate `aidaTable` objects from database queries (Oracle, PostgreSQL, SQLite).
  - Load data from `aidaTable` objects into PostgreSQL or SQLite databases.
- **Data Export:** Export data represented by `aidaTable` objects into CSV format.
- **Helper Utilities:** Includes functions for UID manipulation, XML parsing (`xml2xdict`), array handling, and data type conversions specific to the ASDM context.

## Core Concepts & Classes

- **`ASDMIndex`**: Represents the `ASDM.xml` file for a given ASDM UID. Allows listing the contained tables, their row counts, and their respective UIDs.
- **`ASDMTable`**: Represents a specific table within an ASDM (e.g., `Main`, `SpectralWindow`, `Antenna`). It fetches the table's XML or binary data based on its UID and provides methods (`getTable`, `getFields`, `getValue`) to access its content. Handles the distinction between XML-stored and binary-stored tables.
- **`aidaTable`**: A generic table object. It can be populated from various sources like an `ASDMTable`, `ASDMIndex`, or a database query result. It provides methods for data manipulation, exporting (`getCSV`), and loading data into databases (`toRamDb`, `toAidaDb`).
- **`APDMTable`**: (Assumed Purpose) Likely represents tables from the ALMA Proposal Data Model (APDM), functioning similarly to `ASDMTable` for proposal-related XML data.

## Prerequisites

1. **Python:** Python 3.x recommended.
2. **Python Libraries:**
   - `cx_Oracle`: For connecting to the ALMA Oracle metadata database.
   - `psycopg2`: For connecting to the PostgreSQL `aidadb`.
   - *(Other standard libraries like `os`, `subprocess`, `xml.etree.ElementTree`, `time`, `ast`, `urllib`, `random`, `sqlite3` are typically included with Python)*
3. **Oracle Client:** Oracle Instant Client or full client installed and configured (e.g., `LD_LIBRARY_PATH`, `TNS_ADMIN`).
4. **Database Access:** Credentials and network access to the relevant ALMA Oracle metadata database (SCO or OSF) and potentially a PostgreSQL database (`aidadb`).
5. **AIDA Environment (for Binary Tables):** Access to a configured AIDA environment is required for fetching and processing binary ASDM tables using the `get*.py` scripts.
6. **NGAS Access (for Binary Tables):** Network access to ALMA NGAS servers for retrieving binary data files.
7. **Configuration File:** A Python file (e.g., `archiveConf.py`) containing database connection details and NGAS server information.

## Configuration

**Example `archiveConf.py` Structure:**

```python
# archiveConf.py

db = {
    'sco': 'username/password@sco_tns_alias',
    'osf': 'username/password@osf_tns_alias',
    'aidadb': 'dbname=aidadb user=user password=pw host=localhost'
}

ngas_default = [
    'ngas-server1.example.org',
    'ngas-server2.example.org',
]
````

## Installation

Currently, installation via pip is not configured. Clone the repository:

```bash
git clone <repository_url>
cd qatools
```

Ensure the library directory is in your PYTHONPATH or install it locally:

```bash
pip install .
```

## Basic Usage

```python
import qatools
from qatools import create_conn_metadata_sco, create_conn_aidadb

# --- Setup Connections ---
try:
    create_conn_metadata_sco()
    # create_conn_aidadb()
    print("Database connections established.")
except Exception as e:
    print(f"Error establishing database connections: {e}")

# --- Working with ASDMIndex ---
asdm_uid = 'uid://X1/X1/X1'  # Replace with a valid UID
try:
    asdm_index = qatools.ASDMIndex(asdm_uid)
    print(f"ASDM Creation Time: {asdm_index.timeofcreation}")

    table_dict = asdm_index.getDict()
    print("\nTables in ASDM:")
    for name, info in table_dict.items():
        print(f"- {name}: {info[0]} rows, UID: {info[1]}")

    table_list = asdm_index.getTable()

except Exception as e:
    print(f"Error processing ASDMIndex for {asdm_uid}: {e}")

# --- Working with ASDMTable ---
main_table_uid = table_dict.get('MainTable', (0, ''))[1]

if main_table_uid:
    try:
        main_table = qatools.ASDMTable('MainTable', main_table_uid)

        print(f"\nMainTable is binary: {main_table.is_bin}")
        print(f"MainTable XML Timestamp: {main_table.timestamp}")

        print(f"Defined fields for MainTable: {main_table.allfields}")

        if not main_table.is_bin:
            present_fields = main_table.getFields()
            print(f"Present fields in MainTable instance: {present_fields}")

        table_data = main_table.getTable()
        print("\nMainTable Data (first 5 rows):")
        for row in table_data[:5]:
            print(row)

        scan_numbers = main_table.getValue('scanNumber')
        print(f"\nScan Numbers: {scan_numbers[:10]}")

        first_scan_number = main_table.getValue('scanNumber', rownum=1)
        print(f"Scan Number for row 1: {first_scan_number}")

    except Exception as e:
        print(f"Error processing ASDMTable MainTable ({main_table_uid}): {e}")
else:
    print("\nMainTable not found or is empty.")

# --- Working with aidaTable ---
try:
    aida_main = qatools.aidaTable()
    aida_main.fromASDMTable(main_table)

    csv_output = aida_main.getCSV(separator='|')
    print("\nMainTable as CSV (first 200 chars):")
    print(csv_output[:200] + "...")

    # Example for loading to RAM DB
    # aida_main.toRamDb(drop=True)
    # print("\nLoaded MainTable data into in-memory SQLite DB.")

except Exception as e:
    print(f"Error working with aidaTable: {e}")
```

## Data Model Reference

This library interacts with the ALMA Science Data Model. For details on ASDM tables and fields, refer to the official documentation:
http://almasw.hq.eso.org/almasw/pub/HLA/ASDMImplementation2FBT/SDMTables_postSDM2FBT.pdf
