import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from folium.plugins import MarkerCluster, Fullscreen
from PIL import Image
import os

# ==========================================
# 1. إعدادات المنصة والهوية البصرية (UI/UX)
# ==========================================
# محاولة تحميل لوجو الهيئة، وإذا لم يجده يضع أيقونة افتراضية
try:
    page_icon = Image.open('logo.jpg')
except:
    page_icon = "🏥"

st.set_page_config(
    page_title="مستشفيات الهيئة العامة للرعاية الصحية | EHA",
    page_icon=page_icon,
    layout="wide"
)

# ==========================================
# 2. نظام اللغتين (Bilingual Setup)
# ==========================================
# زر اختيار اللغة في القائمة الجانبية (يجب أن يكون قبل تنسيق CSS)
lang_choice = st.sidebar.radio("🌐 اللغة / Language", ["العربية", "English"])
is_arabic = lang_choice == "العربية"

# قاموس الترجمة لواجهة المستخدم
loc = {
    "title": "🏥 خريطة مستشفيات الهيئة العامة للرعاية الصحية - جمهورية مصر العربية" if is_arabic else "🏥 Egypt Healthcare Authority (EHA) Hospitals Map",
    "search": "🔍 ابحث عن مستشفى محدد:" if is_arabic else "🔍 Search for a specific hospital:",
    "filter_gov": "📍 تصفية حسب المحافظة:" if is_arabic else "📍 Filter by Governorate:",
    "live_data": "عرض البيانات الحية لعدد" if is_arabic else "Live data display for",
    "facilities": "منشأة طبية مفعلة." if is_arabic else "active medical facilities.",
    "kpi_count": "عدد المستشفيات" if is_arabic else "Total Hospitals",
    "kpi_perf": "متوسط الأداء العام" if is_arabic else "Average Performance",
    "kpi_govs": "المحافظات المشمولة" if is_arabic else "Covered Governorates",
    "kpi_specs": "التخصصات النادرة" if is_arabic else "Rare Specialties",
    "specs_val": "8 تخصصات" if is_arabic else "8 Specialties",
    "map_title": "🌍 الخريطة التفاعلية للمنشآت" if is_arabic else "🌍 Interactive Facilities Map",
    "chart_title": "📊 تحليل مؤشرات الكفاءة" if is_arabic else "📊 Performance Indicators Analysis",
    "table_title": "📋 تفاصيل المنشآت الطبية" if is_arabic else "📋 Medical Facilities Details",
    "no_data": "يرجى اختيار محافظة واحدة على الأقل لعرض البيانات." if is_arabic else "Please select at least one governorate to view data."
}

# تنسيق CSS بناءً على اللغة المختارة
if is_arabic:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-right: 5px solid #007bff; border-left: none; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Roboto', sans-serif; direction: ltr; text-align: left; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #007bff; border-right: none; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. إدارة البيانات (Data Management)
# ==========================================
@st.cache_data
def load_data():
    hospitals = {
        'الاسم_AR': [
            'مستشفى النصر التخصصي', 'مستشفى فايد التخصصي', 'مستشفى الكرنك الدولي', 
            'مستشفى شرم الشيخ الدولي', 'مستشفى الرمد ببورسعيد', 'مستشفى طابا المركزي',
            'مستشفى إيزيس التخصصي', 'مستشفى أبو خليفة للطوارئ'
        ],
        'الاسم_EN': [
            'Al Nasr Specialist Hospital', 'Fayed Specialist Hospital', 'Karnak International Hospital', 
            'Sharm El-Sheikh International', 'Port Said Eye Hospital', 'Taba Central Hospital',
            'Isis Specialist Hospital', 'Abu Khalifa Emergency Hospital'
        ],
        'المحافظة_AR': ['بورسعيد', 'الإسماعيلية', 'الأقصر', 'جنوب سيناء', 'بورسعيد', 'جنوب سيناء', 'الأقصر', 'الإسماعيلية'],
        'المحافظة_EN': ['Port Said', 'Ismailia', 'Luxor', 'South Sinai', 'Port Said', 'South Sinai', 'Luxor', 'Ismailia'],
        'lat': [31.2595, 30.4542, 25.6872, 27.9158, 31.2622, 29.4912, 25.6600, 30.6935],
        'lon': [32.2897, 32.3121, 32.6396, 34.3300, 32.3011, 34.8950, 32.6100, 32.3280],
        'كفاءة_الأداء': [95, 88, 92, 97, 90, 85, 94, 96],
        'التخصصات_AR': [
            'جراحة قلب أطفال', 'أوعية دموية', 'زراعة نخاع', 'طب أعماق', 
            'جراحة شبكية', 'طوارئ جبلية', 'نساء وتوليد متقدم', 'جراحات حوادث'
        ],
        'التخصصات_EN': [
            'Pediatric Cardiac Surgery', 'Vascular Surgery', 'Bone Marrow Transplant', 'Hyperbaric Medicine', 
            'Retinal Surgery', 'Mountain Emergency', 'Advanced Obstetrics', 'Trauma Surgeries'
        ],
        'التليفون': ['0663220000', '0643661234', '0952272000', '0693660894', '0663221111', '0693530000', '0952280000', '0643440555'],
        'الإيميل': ['info@nasr.gov.eg', 'fayed@uhia.gov.eg', 'karnak@uhia.gov.eg', 'sharm@uhia.gov.eg', 'ramad@gov.eg', 'taba@gov.eg', 'isis@gov.eg', 'ak@gov.eg']
    }
    return pd.DataFrame(hospitals)

df = load_data()

# تحديد الأعمدة بناءً على اللغة
col_name = 'الاسم_AR' if is_arabic else 'الاسم_EN'
col_gov = 'المحافظة_AR' if is_arabic else 'المحافظة_EN'
col_spec = 'التخصصات_AR' if is_arabic else 'التخصصات_EN'

# ==========================================
# 4. القائمة الجانبية (Sidebar Filters)
# ==========================================
# عرض شعار الهيئة إذا كان موجوداً
if os.path.exists('logo.jpg'):
    st.sidebar.image('logo.jpg', use_container_width=True)
else:
    st.sidebar.warning("⚠️ يرجى وضع صورة 'logo.jpg' في مجلد المشروع.")

st.sidebar.title("نظام التحكم والبحث" if is_arabic else "Control & Search System")
st.sidebar.markdown("---")

search_query = st.sidebar.text_input(loc["search"])
selected_gov = st.sidebar.multiselect(
    loc["filter_gov"],
    options=df[col_gov].unique(),
    default=df[col_gov].unique()
)

# تطبيق الفلاتر
filtered_df = df[df[col_gov].isin(selected_gov)]
if search_query:
    filtered_df = filtered_df[filtered_df[col_name].str.contains(search_query, case=False, na=False)]

# ==========================================
# 5. واجهة العرض الرئيسية (Main Dashboard)
# ==========================================
st.title(loc["title"])

# تأمين الكود ضد الأخطاء إذا كانت القائمة فارغة
if filtered_df.empty:
    st.warning(loc["no_data"])
else:
    st.write(f"{loc['live_data']} **{len(filtered_df)}** {loc['facilities']}")

    # المؤشرات السريعة (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(loc["kpi_count"], len(filtered_df))
    col2.metric(loc["kpi_perf"], f"{int(filtered_df['كفاءة_الأداء'].mean())}%")
    col3.metric(loc["kpi_govs"], filtered_df[col_gov].nunique())
    col4.metric(loc["kpi_specs"], loc["specs_val"])

    st.markdown("---")

    # تقسيم الصفحة إلى خريطة ورسم بياني
    map_col, chart_col = st.columns([2, 1])

    with map_col:
        st.subheader(loc["map_title"])
        m = folium.Map(location=[28.0, 31.0], zoom_start=6, tiles='CartoDB positron')
        Fullscreen().add_to(m)
        marker_cluster = MarkerCluster(name="المستشفيات" if is_arabic else "Hospitals").add_to(m)

        for _, row in filtered_df.iterrows():
            align = "right" if is_arabic else "left"
            dir_str = "rtl" if is_arabic else "ltr"
            font = "Cairo" if is_arabic else "Roboto"
            
            popup_content = f"""
            <div style="direction: {dir_str}; text-align: {align}; font-family: {font}, sans-serif;">
                <h4 style="color: #007bff; margin-bottom: 5px;">{row[col_name]}</h4>
                <p style="margin: 0;"><b>📞 {'التليفون' if is_arabic else 'Phone'}:</b> {row['التليفون']}</p>
                <p style="margin: 0;"><b>📧 {'الإيميل' if is_arabic else 'Email'}:</b> {row['الإيميل']}</p>
                <hr style="margin: 10px 0;">
                <p style="margin: 0; color: green;"><b>📈 {'كفاءة الأداء' if is_arabic else 'Performance'}: {row['كفاءة_الأداء']}%</b></p>
                <p style="margin: 0; color: red;"><b>✨ {'تخصص نادر' if is_arabic else 'Specialty'}: {row[col_spec]}</b></p>
            </div>
            """
            folium.Marker(
                location=[row['lat'], row['lon']],
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=row[col_name],
                icon=folium.Icon(color='blue', icon='plus', prefix='fa')
            ).add_to(marker_cluster)

        st_folium(m, width="100%", height=500, returned_objects=[])

    with chart_col:
        st.subheader(loc["chart_title"])
        fig = px.bar(
            filtered_df, 
            x='كفاءة_الأداء', 
            y=col_name, 
            orientation='h',
            color='كفاءة_الأداء',
            color_continuous_scale='RdYlGn',
            labels={'كفاءة_الأداء': 'النسبة المئوية' if is_arabic else 'Percentage', col_name: ''}
        )
        fig.update_layout(showlegend=False, height=500, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    # جدول البيانات التفصيلي في الأسفل
    st.subheader(loc["table_title"])
    display_cols = [col_name, col_gov, 'التليفون', col_spec, 'كفاءة_الأداء']
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")
st.caption("تم تطوير هذا النظام بواسطة Nesrin Ali  - الهيئة العامة للرعاية الصحية 2026" if is_arabic else "Developed by Nesrin Ali - Egypt Healthcare Authority 2026")
