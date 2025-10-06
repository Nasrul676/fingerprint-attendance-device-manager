import pyodbc
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AttendanceRecordProcessor:
    """
    Kelas untuk memproses data absensi karyawan dari FPLog dan gagalabsens
    ke tabel attrecords dengan logic bisnis yang lengkap.
    """
    
    def __init__(self, connection_string: str):
        """
        Initialize dengan connection string SQL Server
        
        Args:
            connection_string: String koneksi ke SQL Server
        """
        self.conn_string = connection_string
        self.conn = None
        
    def connect(self):
        """Membuat koneksi ke database"""
        try:
            self.conn = pyodbc.connect(self.conn_string)
            logger.info("✅ Koneksi database berhasil")
        except Exception as e:
            logger.error(f"❌ Error koneksi database: {e}")
            raise
    
    def disconnect(self):
        """Menutup koneksi database"""
        if self.conn:
            self.conn.close()
            logger.info("🔌 Koneksi database ditutup")
    
    def parse_pins(self, pins: Optional[str]) -> List[str]:
        """
        Parsing string PIN yang dipisahkan koma
        
        Args:
            pins: String PIN separated by comma (e.g., "123,456,789")
            
        Returns:
            List of PIN strings
        """
        if not pins or not pins.strip():
            return []
        
        pin_list = [p.strip() for p in pins.split(',') if p.strip()]
        logger.info(f"📌 Filter PIN aktif: {len(pin_list)} PIN")
        return pin_list
    
    def get_calendar_data(self, start_date: date, end_date: date, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 1: Membuat kalender (kombinasi unik PIN dan tanggal)
        dari FPLog dan gagalabsens
        """
        logger.info("📅 Membuat kalender data...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND f.PIN IN ('{pins_str}')"
        
        query_fplog = f"""
        SELECT DISTINCT f.PIN, CONVERT(DATE, f.date) as tgl 
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine IN ('102','104','105','106','201','203','1','2','3','4')
          {pin_filter}
        """
        
        query_gagal = f"""
        SELECT DISTINCT g.pin, CONVERT(DATE, g.tgl) as tgl
        FROM gagalabsens g
        WHERE CONVERT(DATE, g.tgl) BETWEEN '{start_date}' AND '{end_date}'
          {pin_filter.replace('f.PIN', 'g.PIN')}
        """
        
        df_fplog = pd.read_sql(query_fplog, self.conn)
        df_gagal = pd.read_sql(query_gagal, self.conn)
        
        df_calendar = pd.concat([df_fplog, df_gagal], ignore_index=True)
        df_calendar = df_calendar.drop_duplicates()
        
        logger.info(f"  ✓ Kalender dibuat: {len(df_calendar)} record")
        return df_calendar
    
    def get_checkin_data(self, start_date: date, end_date: date, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 2: Mengambil data check-in (masuk) dari berbagai sumber
        """
        logger.info("🚪 Mengambil data check-in...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND f.PIN IN ('{pins_str}')"
        
        # Query 1: Mesin 104 status I
        query1 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '104' AND f.status = 'I'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 2: Mesin 105 status I
        query2 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '105' AND f.status = 'I'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 3: gagalabsens mesin 104, 114
        query3 = f"""
        SELECT CONVERT(DATE, g.tgl) as tgl, g.PIN, CONVERT(VARCHAR, MIN(g.tgl), 8) as masuk
        FROM gagalabsens g
        WHERE CONVERT(DATE, g.tgl) BETWEEN '{start_date}' AND '{end_date}'
          AND g.Machine IN ('104', '114')
          {pin_filter.replace('f.PIN', 'g.PIN')}
        GROUP BY CONVERT(DATE, g.tgl), g.PIN
        """
        
        # Query 4: Mesin 2, 3
        query4 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine IN ('2', '3')
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 5: Mesin 1 (kondisi khusus 7-11 Maret 2022)
        query5 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '2022-03-07' AND '2022-03-11'
          AND f.Machine = '1'
          AND f.PIN NOT IN (
              SELECT f2.PIN FROM FPLog f2 
              WHERE CONVERT(DATE, f2.date) BETWEEN '2022-03-07' AND '2022-03-10'
                AND f2.Machine = '2'
          )
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 6: Mesin 201 status P1 MASUK-1
        query6 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '201' AND f.status = 'P1 MASUK-1'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Gabungkan semua query
        dfs = []
        for i, query in enumerate([query1, query2, query3, query4, query5, query6], 1):
            try:
                df = pd.read_sql(query, self.conn)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"  ⚠️ Query {i} error: {e}")
        
        df_masuk = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        
        # Ambil waktu masuk paling awal per PIN per tanggal
        if not df_masuk.empty:
            df_masuk = df_masuk.groupby(['tgl', 'PIN'], as_index=False)['masuk'].min()
        
        logger.info(f"  ✓ Data check-in: {len(df_masuk)} record")
        return df_masuk
    
    def get_checkin_production(self, start_date: date, end_date: date, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 3: Mengambil data check-in produksi
        """
        logger.info("🏭 Mengambil data check-in produksi...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND f.PIN IN ('{pins_str}')"
        
        query1 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MIN(f.Date), 8) as masuk_produksi
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine IN ('108', '110', '111') AND f.status = 'I'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        query2 = f"""
        SELECT CONVERT(DATE, g.tgl) as tgl, g.PIN, CONVERT(VARCHAR, MIN(g.tgl), 8) as masuk_produksi
        FROM gagalabsens g
        WHERE CONVERT(DATE, g.tgl) BETWEEN '{start_date}' AND '{end_date}'
          AND g.Machine IN ('204')
          {pin_filter.replace('f.PIN', 'g.PIN')}
        GROUP BY CONVERT(DATE, g.tgl), g.PIN
        """
        
        df1 = pd.read_sql(query1, self.conn)
        df2 = pd.read_sql(query2, self.conn)
        
        df_prod = pd.concat([df1, df2], ignore_index=True)
        if not df_prod.empty:
            df_prod = df_prod.groupby(['tgl', 'PIN'], as_index=False)['masuk_produksi'].min()
        
        logger.info(f"  ✓ Data check-in produksi: {len(df_prod)} record")
        return df_prod
    
    def get_checkout_data(self, start_date: date, end_date: date, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 4: Mengambil data check-out (keluar)
        """
        logger.info("🚪 Mengambil data check-out...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND f.PIN IN ('{pins_str}')"
        
        # Query 1: Mesin 102 (status bukan '1')
        query1 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MAX(f.Date), 8) as keluar
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '102' AND f.status <> '1'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 2: Mesin 105 status O
        query2 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MAX(f.Date), 8) as keluar
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '105' AND f.status = 'O'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 3: gagalabsens mesin 102, 112
        query3 = f"""
        SELECT CONVERT(DATE, g.tgl) as tgl, g.PIN, CONVERT(VARCHAR, MAX(g.tgl), 8) as keluar
        FROM gagalabsens g
        WHERE CONVERT(DATE, g.tgl) BETWEEN '{start_date}' AND '{end_date}'
          AND g.Machine IN ('102', '112')
          {pin_filter.replace('f.PIN', 'g.PIN')}
        GROUP BY CONVERT(DATE, g.tgl), g.PIN
        """
        
        # Query 4: Mesin 1, 4
        query4 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MAX(f.Date), 8) as keluar
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine IN ('1', '4')
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        # Query 5: Mesin 203 status P1 PULANG-2
        query5 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MAX(f.Date), 8) as keluar
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine = '203' AND f.status = 'P1 PULANG-2'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        dfs = []
        for query in [query1, query2, query3, query4, query5]:
            try:
                df = pd.read_sql(query, self.conn)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"  ⚠️ Query error: {e}")
        
        df_keluar = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
        
        if not df_keluar.empty:
            df_keluar = df_keluar.groupby(['tgl', 'PIN'], as_index=False)['keluar'].max()
        
        logger.info(f"  ✓ Data check-out: {len(df_keluar)} record")
        return df_keluar
    
    def get_checkout_production(self, start_date: date, end_date: date, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 5: Mengambil data check-out produksi
        """
        logger.info("🏭 Mengambil data check-out produksi...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND f.PIN IN ('{pins_str}')"
        
        query1 = f"""
        SELECT CONVERT(DATE, f.date) as tgl, f.PIN, CONVERT(VARCHAR, MAX(f.Date), 8) as keluar_produksi
        FROM FPLog f
        WHERE CONVERT(DATE, f.date) BETWEEN '{start_date}' AND '{end_date}'
          AND f.Machine IN ('108', '110', '111') AND f.status = 'O'
          {pin_filter}
        GROUP BY CONVERT(DATE, f.date), f.PIN
        """
        
        query2 = f"""
        SELECT CONVERT(DATE, g.tgl) as tgl, g.PIN, CONVERT(VARCHAR, MAX(g.tgl), 8) as keluar_produksi
        FROM gagalabsens g
        WHERE CONVERT(DATE, g.tgl) BETWEEN '{start_date}' AND '{end_date}'
          AND g.Machine IN ('202')
          {pin_filter.replace('f.PIN', 'g.PIN')}
        GROUP BY CONVERT(DATE, g.tgl), g.PIN
        """
        
        df1 = pd.read_sql(query1, self.conn)
        df2 = pd.read_sql(query2, self.conn)
        
        df_prod = pd.concat([df1, df2], ignore_index=True)
        if not df_prod.empty:
            df_prod = df_prod.groupby(['tgl', 'PIN'], as_index=False)['keluar_produksi'].max()
        
        logger.info(f"  ✓ Data check-out produksi: {len(df_prod)} record")
        return df_prod
    
    def map_department_name(self, row: pd.Series) -> str:
        """
        Mapping department name berdasarkan lokasi dan jabatan
        """
        # Jika ada deptname dari tabel departments, gunakan itu
        if pd.notna(row.get('deptname_original')) and row['deptname_original'].strip():
            return row['deptname_original']
        
        lokasi = str(row.get('lokasi', '')).strip().upper()
        jabatan = str(row.get('jabatan', '')).strip().upper()
        
        # Mapping berdasarkan lokasi
        if lokasi == 'P1':
            if any(x in jabatan for x in ['MANAGER', 'SUPERVISOR']):
                return 'Management P1'
            elif 'OPERATOR' in jabatan:
                return 'Production P1'
            elif 'HELPER' in jabatan:
                return 'Support P1'
            elif 'STAFF' in jabatan:
                return 'Administration P1'
            else:
                return 'General P1'
        
        elif lokasi == 'P2':
            if any(x in jabatan for x in ['MANAGER', 'SUPERVISOR']):
                return 'Management P2'
            elif 'OPERATOR' in jabatan:
                return 'Production P2'
            elif 'HELPER' in jabatan:
                return 'Support P2'
            elif 'STAFF' in jabatan:
                return 'Administration P2'
            else:
                return 'General P2'
        
        elif lokasi == 'P3':
            if any(x in jabatan for x in ['MANAGER', 'SUPERVISOR']):
                return 'Management P3'
            elif 'OPERATOR' in jabatan:
                return 'Production P3'
            elif 'HELPER' in jabatan:
                return 'Support P3'
            elif 'STAFF' in jabatan:
                return 'Administration P3'
            elif 'SALES' in jabatan:
                return 'Sales P3'
            else:
                return 'General P3'
        
        elif lokasi == 'PELET':
            return 'Production Pelet'
        elif lokasi == 'BLOWING':
            return 'Production Blowing'
        elif lokasi == 'KARUNG':
            return 'Production Karung'
        elif not lokasi or lokasi == '-':
            return 'Unassigned'
        else:
            return f'Department {lokasi}'
    
    def determine_keterangan(self, row: pd.Series, today: date) -> str:
        """
        Menentukan keterangan (Terlambat, Tidak C/In, Tidak C/Out)
        berdasarkan logic bisnis
        """
        masuk = row.get('masuk')
        keluar = row.get('keluar')
        shift = str(row.get('shift', '')).strip()
        tgl = row['tgl']
        
        # Tidak C/In
        if pd.isna(masuk) and pd.notna(keluar) and keluar > '14:00:00':
            return 'Tidak C/In'
        
        # Tidak C/Out
        if pd.isna(keluar) and pd.notna(masuk) and masuk < '18:00:00' and tgl != today:
            return 'Tidak C/Out'
        
        # Cek terlambat untuk Non shift 1
        if pd.notna(masuk) and shift == 'Non shift 1':
            if tgl < date(2024, 3, 7) and masuk > '08:00:00':
                return 'Terlambat'
            elif tgl >= date(2024, 3, 7) and masuk > '07:55:00':
                return 'Terlambat'
        
        # Cek terlambat untuk shift lainnya
        if pd.notna(masuk) and shift != 'Non shift 1':
            # Sebelum 17 Jan 2022
            if tgl < date(2022, 1, 17):
                if '07:05:00' <= masuk <= '09:00:00':
                    return 'Terlambat'
                elif '15:05:00' <= masuk <= '17:00:00':
                    return 'Terlambat'
                elif '19:05:00' <= masuk <= '21:00:00':
                    return 'Terlambat'
                elif '23:05:00' <= masuk <= '23:59:59':
                    return 'Terlambat'
                elif '00:01:00' <= masuk <= '02:59:59':
                    return 'Terlambat'
            
            # Setelah 17 Jan 2022
            else:
                if '06:55:00' <= masuk <= '09:00:00':
                    return 'Terlambat'
                elif '14:55:00' <= masuk <= '17:00:00':
                    return 'Terlambat'
                elif '18:55:00' <= masuk <= '21:00:00':
                    return 'Terlambat'
                elif '22:55:00' <= masuk <= '23:59:59':
                    return 'Terlambat'
                elif '00:05:00' <= masuk <= '02:59:59':
                    return 'Terlambat'
        
        return None
    
    def build_attendance_records(self, df_calendar: pd.DataFrame, df_masuk: pd.DataFrame,
                                df_keluar: pd.DataFrame, df_masuk_prod: pd.DataFrame,
                                df_keluar_prod: pd.DataFrame, pin_list: List[str]) -> pd.DataFrame:
        """
        Tahap 6: Menggabungkan semua data dan JOIN dengan employees & departments
        """
        logger.info("🔨 Membangun attendance records...")
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND e.pin IN ('{pins_str}')"
        
        # Ambil data employees dan departments
        query_emp = f"""
        SELECT e.pin, e.name, e.jabatan, e.lokasi, 
               ISNULL(e.shift, 'Belum di set') as shift,
               d.deptname as deptname_original
        FROM employees e
        LEFT JOIN departments d ON d.id = e.department
        WHERE e.status IN ('Active', 'Resign')
          {pin_filter}
        """
        
        df_emp = pd.read_sql(query_emp, self.conn)
        
        # Merge dengan calendar
        df = df_calendar.merge(df_emp, left_on='PIN', right_on='pin', how='inner')
        
        # Merge dengan data masuk
        df = df.merge(df_masuk, on=['tgl', 'PIN'], how='left')
        
        # Merge dengan data keluar
        df = df.merge(df_keluar, on=['tgl', 'PIN'], how='left')
        
        # Merge dengan data masuk produksi
        df = df.merge(df_masuk_prod, on=['tgl', 'PIN'], how='left')
        
        # Merge dengan data keluar produksi
        df = df.merge(df_keluar_prod, on=['tgl', 'PIN'], how='left')
        
        # Mapping department name
        df['deptname'] = df.apply(self.map_department_name, axis=1)
        
        # Tentukan keterangan
        today = date.today()
        df['keterangan'] = df.apply(lambda row: self.determine_keterangan(row, today), axis=1)
        
        # Select kolom yang diperlukan
        df = df[['tgl', 'PIN', 'name', 'jabatan', 'lokasi', 'deptname', 'shift',
                 'masuk', 'keluar', 'masuk_produksi', 'keluar_produksi', 'keterangan']]
        
        # Rename PIN to pin untuk konsistensi
        df = df.rename(columns={'PIN': 'pin'})
        
        # Sort
        df = df.sort_values(['pin', 'tgl'])
        
        logger.info(f"  ✓ Attendance records: {len(df)} record")
        return df
    
    def delete_existing_records(self, start_date: date, end_date: date, pin_list: List[str]) -> int:
        """
        Tahap 7: Hapus data lama dari attrecords
        """
        logger.info("🗑️  Menghapus data lama...")
        
        cursor = self.conn.cursor()
        
        pin_filter = ""
        if pin_list:
            pins_str = "','".join(pin_list)
            pin_filter = f"AND pin IN ('{pins_str}')"
        
        delete_query = f"""
        DELETE FROM attrecords
        WHERE tgl BETWEEN '{start_date}' AND '{end_date}'
          {pin_filter}
        """
        
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount
        self.conn.commit()
        
        logger.info(f"  ✓ Data dihapus: {deleted_count} record")
        return deleted_count
    
    def insert_records(self, df: pd.DataFrame) -> int:
        """
        Tahap 8: Insert data ke attrecords
        """
        logger.info("💾 Menyimpan data ke attrecords...")
        
        cursor = self.conn.cursor()
        
        insert_query = """
        INSERT INTO attrecords(tgl, pin, name, jabatan, lokasi, deptname, shift, 
                              masuk, keluar, masuk_produksi, keluar_produksi, keterangan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Prepare data
        records = []
        for _, row in df.iterrows():
            records.append((
                row['tgl'],
                row['pin'],
                row['name'],
                row['jabatan'],
                row['lokasi'],
                row['deptname'],
                row['shift'],
                row['masuk'] if pd.notna(row['masuk']) else None,
                row['keluar'] if pd.notna(row['keluar']) else None,
                row['masuk_produksi'] if pd.notna(row['masuk_produksi']) else None,
                row['keluar_produksi'] if pd.notna(row['keluar_produksi']) else None,
                row['keterangan'] if pd.notna(row['keterangan']) else None
            ))
        
        # Batch insert
        cursor.executemany(insert_query, records)
        self.conn.commit()
        
        inserted_count = len(records)
        logger.info(f"  ✓ Data disimpan: {inserted_count} record")
        
        return inserted_count
    
    def process(self, start_date: date, end_date: date, pins: Optional[str] = None) -> Dict[str, Any]:
        """
        Main process: Eksekusi seluruh tahapan pemrosesan attendance records
        
        Args:
            start_date: Tanggal awal
            end_date: Tanggal akhir
            pins: String PIN yang dipisahkan koma (opsional)
            
        Returns:
            Dictionary berisi summary hasil proses
        """
        start_time = datetime.now()
        logger.info("=" * 70)
        logger.info("🚀 MULAI PROSES ATTENDANCE RECORD")
        logger.info(f"📆 Periode: {start_date} s/d {end_date}")
        
        try:
            # Connect database
            self.connect()
            
            # Parse PIN filter
            pin_list = self.parse_pins(pins)
            
            # Tahap 1: Buat kalender
            df_calendar = self.get_calendar_data(start_date, end_date, pin_list)
            
            if df_calendar.empty:
                logger.warning("⚠️  Tidak ada data untuk diproses")
                return {
                    'status': 'warning',
                    'message': 'Tidak ada data untuk diproses',
                    'records_inserted': 0
                }
            
            # Tahap 2-5: Ambil semua data check-in/out
            df_masuk = self.get_checkin_data(start_date, end_date, pin_list)
            df_masuk_prod = self.get_checkin_production(start_date, end_date, pin_list)
            df_keluar = self.get_checkout_data(start_date, end_date, pin_list)
            df_keluar_prod = self.get_checkout_production(start_date, end_date, pin_list)
            
            # Tahap 6: Build attendance records lengkap
            df_attendance = self.build_attendance_records(
                df_calendar, df_masuk, df_keluar, df_masuk_prod, df_keluar_prod, pin_list
            )
            
            # Tahap 7: Hapus data lama
            deleted_count = self.delete_existing_records(start_date, end_date, pin_list)
            
            # Tahap 8: Insert data baru
            inserted_count = self.insert_records(df_attendance)
            
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            logger.info("=" * 70)
            logger.info("✅ PROSES SELESAI")
            logger.info(f"⏱️  Waktu eksekusi: {elapsed_time:.2f} detik")
            logger.info(f"📊 Record dihapus: {deleted_count}")
            logger.info(f"📊 Record diinsert: {inserted_count}")
            logger.info("=" * 70)
            
            return {
                'status': 'success',
                'message': 'Proses berhasil',
                'records_deleted': deleted_count,
                'records_inserted': inserted_count,
                'date_from': start_date,
                'date_to': end_date,
                'pins_filter': pins,
                'execution_time_seconds': elapsed_time,
                'processed_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e),
                'records_inserted': 0
            }
        
        finally:
            # Selalu disconnect
            self.disconnect()


# =====================================
# CONTOH PENGGUNAAN
# =====================================

def main():
    """
    Contoh penggunaan AttendanceRecordProcessor
    """
    
    # 1. Setup connection string
    # Sesuaikan dengan konfigurasi SQL Server Anda
    connection_string = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'  # atau IP server
        'DATABASE=attendance_db;'         # nama database
        'UID=sa;'                         # username
        'PWD=your_password;'              # password
        'TrustServerCertificate=yes;'
    )
    
    # 2. Inisialisasi processor
    processor = AttendanceRecordProcessor(connection_string)
    
    # 3. CONTOH 1: Proses semua PIN untuk periode tertentu
    print("\n" + "="*70)
    print("CONTOH 1: Proses semua karyawan")
    print("="*70)
    
    result = processor.process(
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31)
    )
    
    print(f"\nHasil: {result}")
    
    # 4. CONTOH 2: Proses hanya PIN tertentu
    print("\n" + "="*70)
    print("CONTOH 2: Proses karyawan dengan PIN spesifik")
    print("="*70)
    
    result = processor.process(
        start_date=date(2024, 2, 1),
        end_date=date(2024, 2, 29),
        pins="123,456,789"  # Filter PIN spesifik
    )
    
    print(f"\nHasil: {result}")
    
    # 5. CONTOH 3: Proses bulan ini
    print("\n" + "="*70)
    print("CONTOH 3: Proses bulan ini")
    print("="*70)
    
    today = date.today()
    first_day = date(today.year, today.month, 1)
    
    result = processor.process(
        start_date=first_day,
        end_date=today
    )
    
    print(f"\nHasil: {result}")


# =====================================
# SCRIPT ALTERNATIF: PROSES DARI CSV
# =====================================

def process_from_csv_config(config_file: str):
    """
    Proses attendance berdasarkan konfigurasi dari file CSV
    
    Format CSV:
    start_date,end_date,pins
    2024-01-01,2024-01-31,
    2024-02-01,2024-02-29,"123,456"
    """
    import csv
    
    # Baca konfigurasi
    with open(config_file, 'r') as f:
        reader = csv.DictReader(f)
        configs = list(reader)
    
    # Setup connection
    connection_string = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=attendance_db;'
        'Trusted_Connection=yes;'  # Windows Authentication
    )
    
    processor = AttendanceRecordProcessor(connection_string)
    
    # Proses setiap baris
    results = []
    for config in configs:
        start_date = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(config['end_date'], '%Y-%m-%d').date()
        pins = config.get('pins', '').strip() or None
        
        result = processor.process(start_date, end_date, pins)
        results.append(result)
    
    return results


# =====================================
# SCRIPT UNTUK SCHEDULED TASK
# =====================================

def daily_attendance_sync():
    """
    Script untuk sinkronisasi harian (bisa dijadwalkan via cron/task scheduler)
    Proses data kemarin
    """
    from datetime import timedelta
    
    yesterday = date.today() - timedelta(days=1)
    
    connection_string = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=attendance_db;'
        'Trusted_Connection=yes;'
    )
    
    processor = AttendanceRecordProcessor(connection_string)
    
    # Proses data kemarin
    result = processor.process(
        start_date=yesterday,
        end_date=yesterday
    )
    
    # Log hasil
    if result['status'] == 'success':
        print(f"✅ Daily sync berhasil: {result['records_inserted']} records")
    else:
        print(f"❌ Daily sync gagal: {result['message']}")
    
    return result


def weekly_attendance_sync():
    """
    Script untuk sinkronisasi mingguan
    Proses data 7 hari terakhir
    """
    from datetime import timedelta
    
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    connection_string = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost\\SQLEXPRESS;'
        'DATABASE=attendance_db;'
        'Trusted_Connection=yes;'
    )
    
    processor = AttendanceRecordProcessor(connection_string)
    
    result = processor.process(
        start_date=week_ago,
        end_date=today
    )
    
    if result['status'] == 'success':
        print(f"✅ Weekly sync berhasil: {result['records_inserted']} records")
    else:
        print(f"❌ Weekly sync gagal: {result['message']}")
    
    return result


# =====================================
# UTILITY FUNCTIONS
# =====================================

def export_attendance_to_excel(start_date: date, end_date: date, 
                               output_file: str, connection_string: str):
    """
    Export hasil attendance records ke Excel
    """
    import pyodbc
    
    conn = pyodbc.connect(connection_string)
    
    query = f"""
    SELECT tgl, pin, name, jabatan, lokasi, deptname, shift,
           masuk, keluar, masuk_produksi, keluar_produksi, keterangan
    FROM attrecords
    WHERE tgl BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY pin, tgl
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Export ke Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
        
        # Format kolom
        worksheet = writer.sheets['Attendance']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    logger.info(f"📊 Data exported to: {output_file}")


def get_attendance_summary(start_date: date, end_date: date, connection_string: str):
    """
    Mendapatkan ringkasan attendance
    """
    import pyodbc
    
    conn = pyodbc.connect(connection_string)
    
    query = f"""
    SELECT 
        deptname,
        COUNT(*) as total_records,
        SUM(CASE WHEN keterangan = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
        SUM(CASE WHEN keterangan = 'Tidak C/In' THEN 1 ELSE 0 END) as tidak_cin,
        SUM(CASE WHEN keterangan = 'Tidak C/Out' THEN 1 ELSE 0 END) as tidak_cout,
        SUM(CASE WHEN keterangan IS NULL THEN 1 ELSE 0 END) as normal
    FROM attrecords
    WHERE tgl BETWEEN '{start_date}' AND '{end_date}'
    GROUP BY deptname
    ORDER BY deptname
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df


# =====================================
# ENTRY POINT
# =====================================

if __name__ == "__main__":
    # Uncomment salah satu untuk menjalankan:
    
    # 1. Contoh penggunaan lengkap
    main()
    
    # 2. Daily sync (untuk cron job)
    # daily_attendance_sync()
    
    # 3. Weekly sync
    # weekly_attendance_sync()
    
    # 4. Export ke Excel
    # connection_string = "..."
    # export_attendance_to_excel(
    #     date(2024, 1, 1), 
    #     date(2024, 1, 31), 
    #     'attendance_jan2024.xlsx',
    #     connection_string
    # )