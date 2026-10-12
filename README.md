# MyTools Grid Decision Manager V2

โครงสร้างนี้ออกแบบให้ merge กับของเดิมของนายโดยตรง

## UX ใน Ribbon
```text
MyTools.tab
└── Grid.panel
    ├── Load CSV
    ├── DESIGN
    ├── FIELD
    ├── ADJUST
    ├── ACTIVE
    └── Compare
```

## พฤติกรรม
- Load CSV: เลือก grid CSV และ meta CSV แล้วจำ path ไว้ใน session
- DESIGN/FIELD/ADJUST/ACTIVE: แสดงกริดตาม mode ที่กด
- Compare: สรุปตำแหน่ง 3 ค่าใน dialog
- H grid: อ่าน CSV เป็นบน -> ล่าง แล้ว script reverse เพื่อแสดงใน Revit ให้ถูกทิศ
- V grid: อ่านซ้าย -> ขวาตามปกติ

## ตำแหน่งที่ต้อง merge
`Documents/cad_revit_toolkit/pyrevit/MyTools.extension`

## หมายเหตุ
เวอร์ชันนี้ยังไม่มีปุ่ม Save Decision และยังไม่เขียน active_mode กลับลง CSV
