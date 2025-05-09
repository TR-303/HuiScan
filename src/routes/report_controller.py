from datetime import datetime
import os
import uuid
import random
import matplotlib.pyplot as plt

from src.routes.image_controller import get_statistics
from flask import Blueprint, make_response, request
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from src.models import HSImage, HSDefect
from src.config import get_upload_folder

report_bp = Blueprint('report_bp', __name__)

# 注册中文字体
font_path = os.path.join(os.path.dirname(__file__), '..', 'ttc', 'msyh.ttc')
pdfmetrics.registerFont(TTFont('SimHei', font_path))


@report_bp.route('/create-report', methods=['GET'])
def create_report():
    # 获取统计数据
    statistics_response = get_statistics()
    statistics_data = statistics_response.get_json()

    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')

    # 绘制柱状图 (statisticsData)
    bar_dates = statistics_data['statisticsData']['dates']
    total = statistics_data['statisticsData']['total']
    defect = statistics_data['statisticsData']['defect']
    x = range(len(bar_dates))
    plt.bar(x, total, width=0.4, label='总数', align='center')
    plt.bar(x, defect, width=0.4, label='缺陷', align='edge')
    plt.xticks(x, bar_dates, fontproperties="SimHei")
    plt.title('每日检测统计', fontproperties="SimHei")
    plt.xlabel('日期', fontproperties="SimHei")
    plt.ylabel('数量', fontproperties="SimHei")
    plt.legend(prop={"family": "SimHei"})
    bar_chart_path = f"bar_chart_{uuid.uuid4().hex}.png"
    plt.savefig(bar_chart_path)
    plt.close()

    # 绘制饼图 (proportionData)
    labels = [item['name'] for item in statistics_data['proportionData']]
    sizes = [item['value'] for item in statistics_data['proportionData']]
    plt.pie(sizes, labels=labels, autopct='%1.1f%%', textprops={'fontproperties': "SimHei"})
    plt.title('缺陷比例统计', fontproperties="SimHei")
    pie_chart_path = f"pie_chart_{uuid.uuid4().hex}.png"
    plt.savefig(pie_chart_path)
    plt.close()

    # 绘制折线图 (singleStatisticsData)
    single_dates = statistics_data['singleStatisticsData']['dates']
    for defect_type, values in statistics_data['singleStatisticsData'].items():
        if defect_type != 'dates':
            plt.plot(single_dates, values, label=defect_type, marker='o')
    plt.title('每日缺陷统计', fontproperties="SimHei")
    plt.xlabel('日期', fontproperties="SimHei")
    plt.ylabel('数量', fontproperties="SimHei")
    plt.legend(prop={"family": "SimHei"})
    plt.grid(True)
    line_chart_path = f"line_chart_{uuid.uuid4().hex}.png"
    plt.savefig(line_chart_path)
    plt.close()

    try:
        # 使用 reportlab 生成 PDF
        local_pdf_path = "report.pdf"
        c = canvas.Canvas(local_pdf_path, pagesize=(1000, 1440))
        c.setFont("SimHei", 30)  # 设置中文字体

        # 标题
        c.drawCentredString(500, 1350, "慧识-钢材缺陷检测报告")

        # 副标题
        c.setFont("SimHei", 15)
        c.drawString(50, 1300, f"检测时间段：{start_time} - {end_time}")

        # 次级标题
        c.setFont("SimHei", 20)
        c.drawString(50, 1250, "一、统计数据")

        c.setFont("SimHei", 16)
        c.drawString(50, 1220,
                     f"共检测{sum(statistics_data['statisticsData']['total'])}张图片，其中缺陷图像{sum(statistics_data['statisticsData']['defect'])}张")

        c.setFont("SimHei", 14)

        # 插入柱状图
        c.drawImage(bar_chart_path, 100, 730, width=800)
        c.drawCentredString(500, 710, "图一 每日钢材检测数量统计")

        # 插入饼图
        c.drawImage(pie_chart_path, 200, 110, width=600)
        c.drawCentredString(500, 90, "图二 钢材缺陷类型占比")

        c.showPage()
        c.setFont("SimHei", 14)

        # 插入折线图
        c.drawImage(line_chart_path, 100, 750, width=800)
        c.drawCentredString(500, 730, "图三 各项缺陷数量统计")

        # 次级标题
        c.setFont("SimHei", 20)
        c.drawString(50, 700, "二、典型缺陷展示")

        # 定义缺陷类型及顺序
        defect_types = ["表面杂质", "斑块缺陷", "横线裂纹", "边缘裂纹"]
        y_position = 650  # 初始 y 坐标

        for defect_type in defect_types:
            # 添加再次一级标题
            c.setFont("SimHei", 18)
            c.drawString(70, y_position, f"{defect_types.index(defect_type) + 1}. {defect_type}")
            y_position -= 30

            # 查询对应缺陷类型的图片
            images = HSImage.query.join(HSImage.defects).filter(
                HSDefect.defect_type == defect_type,
                HSImage.detect_time.between(datetime.strptime(start_time, "%Y-%m-%d"),
                                            datetime.strptime(end_time, "%Y-%m-%d"))
            ).all()

            if not images:
                # 如果没有图片，插入提示文字
                c.setFont("SimHei", 14)
                c.drawString(100, y_position, "该缺陷类别没有检测到")
                y_position -= 30
                continue

            # 随机选择最多 5 张图片
            selected_images = random.sample(images, min(len(images), 5))

            for image in selected_images:
                # 插入说明
                c.setFont("SimHei", 12)
                c.drawString(100, y_position, f"检测时间：{image.detect_time}")
                y_position -= 20
                c.drawString(100, y_position, f"检测批次号：{image.batch_id}")
                y_position -= 20
                c.drawString(100, y_position, "检测结果：")
                y_position -= 20

                # 插入图片
                image_path = os.path.join(get_upload_folder(), image.detect_time.strftime('%Y-%m-%d'),
                                          image.image_processed_path)
                # 等比缩放图片到最大宽度800和最大高度200
                scale = min(800 / image.width, 200 / image.height, 1)
                scaled_width = int(image.width * scale)
                scaled_height = int(image.height * scale)
                c.drawImage(image_path, 100, y_position - scaled_height, width=scaled_width, height=scaled_height)
                y_position -= 20 + scaled_height

                # 自动换页处理
                if y_position < 100:
                    c.showPage()
                    c.setFont("SimHei", 18)
                    y_position = 1350

        c.save()

        # 返回 PDF 响应
        with open(local_pdf_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()

        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=report.pdf'
        return response
    finally:
        # 删除临时图片
        os.remove(line_chart_path)
        os.remove(pie_chart_path)
        os.remove(bar_chart_path)
