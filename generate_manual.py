import os

# เนื้อหา Flowchart และคู่มือ
html_content = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Communi-Pharm V30 Manual</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad:true});</script>
    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Sarabun', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        h2 { color: #2980b9; margin-top: 30px; }
        h3 { color: #16a085; }
        .box { border: 1px solid #ddd; padding: 15px; border-radius: 5px; background-color: #f9f9f9; margin-bottom: 20px; }
        .warning { color: #c0392b; font-weight: bold; }
        .mermaid { margin: 20px 0; text-align: center; }
        @media print {
            .no-print { display: none; }
            body { padding: 0; }
            h2 { page-break-before: always; }
            h2:first-of-type { page-break-before: avoid; }
        }
    </style>
</head>
<body>

    <div class="no-print" style="background: #ffeaa7; padding: 10px; text-align: center; border: 1px solid #fdcb6e; margin-bottom: 20px;">
        ⚠️ <b>วิธีบันทึกเป็น PDF:</b> คลิกขวาที่หน้านี้เลือก <b>Print</b> (หรือกด Ctrl+P) > ที่ช่อง Destination เลือก <b>"Save as PDF"</b>
    </div>

    <h1>📚 คู่มือระบบ Communi-Pharm V30</h1>
    <p>เอกสารประกอบการใช้งานโปรแกรมจำลองร้านขายยาและการบริหารจัดการ</p>

    <h2>1. System Flowchart (ผังการทำงานของระบบ)</h2>
    <div class="box">
        <p>ภาพรวมลำดับขั้นตอนการเล่นเกม ตั้งแต่การตั้งค่าของผู้สอน จนถึงการส่งงานของนักศึกษา</p>
    </div>
    <div class="mermaid">
    graph TD
        Start((Start App)) --> RoleSelect{Select Role}
        
        subgraph Instructor [ส่วนของผู้สอน]
            RoleSelect -- Instructor --> Setup1[Step 1: ตั้งจำนวนทีม]
            Setup1 --> Setup2[Step 2: กำหนดน้ำหนักคะแนน<br/>Weights]
            Setup2 --> Setup3[Step 3: กำหนดค่าตลาดเริ่มต้น<br/>Market Env]
            Setup3 --> StartGame[🏁 กด START GAME]
            StartGame --> ActiveState{รอผลลัพธ์}
            ActiveState -- ครบทุกทีม? --> SetupNext[⚙️ Setup Next Period]
            SetupNext --> EditEnv[กำหนดสถานการณ์รอบถัดไป]
            EditEnv --> RunCalc[🧮 กด RUN PERIOD]
            RunCalc --> ActiveState
        end

        subgraph Student [ส่วนของนักศึกษา]
            RoleSelect -- Student --> SelectTeam[เลือกทีม]
            SelectTeam --> CheckPer{ตรวจสอบ Period}
            CheckPer -- Period 1 --> SetupStore[ตั้งชื่อร้าน / เลือกทำเล]
            SetupStore --> InputDec[ตัดสินใจ 36 ตัวแปร]
            CheckPer -- Period > 1 --> InputDec
            InputDec --> Submit[กด Submit]
            Submit --> Wait((รออาจารย์))
            Wait -- อาจารย์กด Run --> ViewRes[📊 ดูผลลัพธ์ / งบการเงิน]
            ViewRes --> InputDec
        end
    </div>

    <h2>2. Logic & Formula Diagram (ผังความสัมพันธ์ตัวแปร)</h2>
    
    <h3>2.1 กลไกส่วนแบ่งตลาด (Market Share Engine)</h3>
    <p>แสดงที่มาของยอดขาย ว่ามาจากการตัดสินใจเรื่อง ราคา, โฆษณา และ เวลาเปิดร้าน อย่างไร</p>
    <div class="mermaid">
    graph TD
        Decisions[การตัดสินใจนักศึกษา] -->|Price/Promo/Hours| ScoreCalc{คำนวณคะแนน}
        Weights[น้ำหนักคะแนนจากอาจารย์] -->|คูณน้ำหนัก| ScoreCalc
        
        ScoreCalc --> TotalScore[คะแนนความสามารถในการแข่งขัน]
        TotalScore -->|เทียบกับคู่แข่ง| MktShare[🏆 ส่วนแบ่งตลาด %]
        
        MarketVol[จำนวนคนไข้รวมในตลาด] -->|คูณ| SalesVol[ยอดขายยาจำนวน Rx]
        MktShare --> SalesVol
        SalesVol --> Revenue[💰 รายได้รวม]
    </div>

    <h3>2.2 กลไกกำไรและค่าใช้จ่าย (Profit & Expense)</h3>
    <p>แสดงความสัมพันธ์ของ ต้นทุน ค่าจ้าง และกำไรสุทธิ</p>
    <div class="mermaid">
    graph LR
        Rev[รายได้รวม] --> GM{กำไรขั้นต้น}
        COGS[ต้นทุนสินค้า] --> GM
        
        subgraph Expenses [ค่าใช้จ่ายดำเนินงาน]
            Staff[ค่าจ้างพนักงาน]
            OT[ค่าล่วงเวลา OT]
            Rent[ค่าเช่า %ยอดขาย]
            Fixed[ค่าใช้จ่ายคงที่]
        end
        
        GM --> NetCalc((คำนวณกำไร))
        Expenses --> NetCalc
        NetCalc --> NetProfit[🏆 กำไรสุทธิ Net Profit]
        
        NetProfit --> CashFlow{กระแสเงินสด}
        CashFlow -- ติดลบ --> Loan[🚨 กู้เงินฉุกเฉิน<br/>ดอกเบี้ย 20%]
    </div>

    <h2>3. คู่มือการใช้งาน (Game Manual)</h2>

    <h3>👨‍🏫 สำหรับผู้สอน (Instructor)</h3>
    <ul>
        <li><b>หน้าที่หลัก:</b> เป็นผู้กำหนดกติกา (Weights) และสร้างสถานการณ์จำลอง (Market Environment)</li>
        <li><b>Step 1-3 Setup:</b> กำหนดจำนวนทีม, ค่าน้ำหนัก (เช่น ลูกค้าชอบของถูก หรือชอบบริการ), และค่าเศรษฐกิจเริ่มต้น</li>
        <li><b>การ Run Period:</b> ห้ามกด Run จนกว่านักเรียนจะส่งครบ (ดูสถานะที่มุมขวาล่าง) ก่อนกด Run สามารถปรับค่า Inflation หรือ Demand เพื่อสร้างโจทย์ยากๆ ได้</li>
    </ul>

    <h3>🎓 สำหรับนักศึกษา (Student)</h3>
    <ul>
        <li><b>เป้าหมาย:</b> สร้างกำไรสูงสุด และรักษาสภาพคล่องทางการเงิน</li>
        <li><b>การตัดสินใจ (Decisions):</b> ท่านต้องกรอกค่า 36 ตัวแปร ทุกรอบ เช่น ราคาขายยา, งบโฆษณา, จำนวนพนักงาน</li>
        <li><b>ข้อควรระวัง:</b>
            <ul>
                <li><span class="warning">Overtime:</span> หากเปิดร้านนานแต่จ้างคนน้อย จะโดนค่า OT (1.5 เท่า)</li>
                <li><span class="warning">Emergency Loan:</span> หากเงินสดติดลบ ระบบจะกู้ให้อัตโนมัติพร้อมดอกเบี้ยมหาโหด</li>
            </ul>
        </li>
    </ul>

    <hr>
    <p style="text-align:center; font-size:0.8em; color:#777;">Generated by Communi-Pharm V30 System</p>
</body>
</html>
"""

# สร้างไฟล์ HTML
filename = "CommuniPharm_Manual_V30.html"
with open(filename, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ สร้างไฟล์สำเร็จ: {filename}")
print(f"👉 กรุณาเปิดไฟล์ {filename} ใน Google Chrome หรือ Edge")
print(f"👉 คลิกขวา เลือก 'Print' -> ตรง Printer เลือก 'Save as PDF'")
