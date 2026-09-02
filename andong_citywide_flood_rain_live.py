import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import geopandas as gpd
import folium


# ============================================================
# 파일 설정
# ============================================================

POINT_FILE = "안동시_전체_침수우려지점.xlsx"

BOUNDARY_FILE = (
    "andong_boundary/bnd_dong_37040_2025_2Q.shp"
)

OUT_FILE = (
    "안동시_침수우려지점_실시간강우_테스트지도.html"
)


print("=" * 75)
print("안동시 침수우려지점 + 119안전센터 최종지도")
print("=" * 75)


# ============================================================
# 1. 119안전센터 관할
# ============================================================

CENTER_AREAS = {

    "법흥119안전센터": [
        "중구동",
        "명륜동",
        "태화동",
        "평화동",
        "안기동",
        "서구동",
        "강남동",
        "일직면",
        "남후면"
    ],

    "용상119안전센터": [
        "용상동",
        "남선면",
        "길안면",
        "임하면",
        "임동면"
    ],

    "풍산119안전센터": [
        "풍산읍",
        "풍천면"
    ],

    "옥동119안전센터": [
        "옥동",
        "송하동",
        "북후면",
        "서후면"
    ],

    "도산119안전센터": [
        "와룡면",
        "도산면",
        "예안면",
        "녹전면"
    ]
}


CENTER_COLORS = {

    "법흥119안전센터": "#00E5FF",
    "용상119안전센터": "#00FF88",
    "풍산119안전센터": "#FFD600",
    "옥동119안전센터": "#D500F9",
    "도산119안전센터": "#FF6D00"
}


# ============================================================
# 2. 읍면동 → 센터 변환표
# ============================================================

AREA_TO_CENTER = {}

for center, areas in CENTER_AREAS.items():

    for area in areas:

        AREA_TO_CENTER[area] = center


# ============================================================
# 3. 침수우려지점 읽기
# ============================================================

print("\n1. 침수우려지점 읽는 중...")


points = pd.read_excel(
    POINT_FILE,
    sheet_name="안동시전체"
)


points["위도"] = pd.to_numeric(
    points["위도"],
    errors="coerce"
)

points["경도"] = pd.to_numeric(
    points["경도"],
    errors="coerce"
)

points["HAND_m"] = pd.to_numeric(
    points["HAND_m"],
    errors="coerce"
)

points["잠재수로거리_m"] = pd.to_numeric(
    points["잠재수로거리_m"],
    errors="coerce"
)


points = points.dropna(
    subset=["위도", "경도"]
).copy()


# ============================================================
# 4. 관할센터 배정
# ============================================================

points["관할119안전센터"] = (
    points["읍면"].map(
        AREA_TO_CENTER
    )
)


print(
    "전체 지점:",
    len(points)
)


# ============================================================
# 5. 지점 수
# ============================================================

count_1 = int(
    (
        points["우려등급"]
        == "1순위 우려지점"
    ).sum()
)

count_2 = int(
    (
        points["우려등급"]
        == "2순위 우려지점"
    ).sum()
)


print(
    "1순위:",
    count_1
)

print(
    "2순위:",
    count_2
)


# ============================================================
# 6. 행정경계
# ============================================================

boundary = gpd.read_file(
    BOUNDARY_FILE
).to_crs(
    "EPSG:4326"
)


boundary["관할119안전센터"] = (
    boundary["ADM_NM"]
    .map(
        AREA_TO_CENTER
    )
)


# ============================================================
# 7. 센터별 경계 통합
# ============================================================

center_boundary = (

    boundary[
        boundary[
            "관할119안전센터"
        ].notna()
    ]

    .dissolve(
        by="관할119안전센터"
    )

    .reset_index()
)


# ============================================================
# 8. 안동 전체 범위
# ============================================================

minx, miny, maxx, maxy = (
    boundary.total_bounds
)

center_lat = (
    miny + maxy
) / 2

center_lon = (
    minx + maxx
) / 2


# ============================================================
# 9. 지도 생성
# ============================================================

m = folium.Map(

    location=[
        center_lat,
        center_lon
    ],

    zoom_start=10,

    tiles=None,

    control_scale=True,

    prefer_canvas=True
)


# ============================================================
# 10. 위성영상
# ============================================================

folium.TileLayer(

    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/"
        "World_Imagery/"
        "MapServer/tile/{z}/{y}/{x}"
    ),

    attr="Esri World Imagery",

    name="위성영상",

    overlay=False,

    control=True,

    show=True,

    max_zoom=19

).add_to(m)


# ============================================================
# 11. 일반지도
# ============================================================

folium.TileLayer(

    tiles="OpenStreetMap",

    name="일반지도",

    overlay=False,

    control=True,

    show=False

).add_to(m)

# ============================================================
# 안동시 외부 반투명 마스킹
# ============================================================

print("안동시 외부 마스킹 적용 중...")


# 안동시 전체 경계 하나로 합치기
andong_union = (
    boundary.geometry
    .union_all()
)


# GeoJSON 형태로 변환
andong_geojson = (
    gpd.GeoSeries(
        [andong_union],
        crs="EPSG:4326"
    )
    .__geo_interface__
)


geom = (
    andong_geojson[
        "features"
    ][0]["geometry"]
)


# 안동시보다 충분히 넓은 외부 사각형
outer = [

    [minx - 2, miny - 2],

    [maxx + 2, miny - 2],

    [maxx + 2, maxy + 2],

    [minx - 2, maxy + 2],

    [minx - 2, miny - 2]

]


# 안동시 경계를 마스크의 구멍으로 사용
holes = []


if geom["type"] == "Polygon":

    holes.append(
        geom["coordinates"][0]
    )


elif geom["type"] == "MultiPolygon":

    for polygon in geom["coordinates"]:

        holes.append(
            polygon[0]
        )


# Folium은 [위도, 경도] 순서
mask_coordinates = [

    [
        [lat, lon]

        for lon, lat in outer
    ]

]


for hole in holes:

    mask_coordinates.append(

        [
            [lat, lon]

            for lon, lat in hole
        ]

    )


# 안동시 바깥을 회색 반투명 처리
folium.Polygon(

    locations=mask_coordinates,

    color="#555555",

    weight=0,

    fill=True,

    fill_color="#555555",

    fill_opacity=0.55,

    # 우려지점 클릭을 방해하지 않게
    interactive=False

).add_to(m)

# ============================================================
# 12. 센터 관할경계
# ============================================================

center_group = folium.FeatureGroup(
    name="119안전센터 관할경계",
    show=True
)


for _, row in center_boundary.iterrows():

    center_name = row[
        "관할119안전센터"
    ]

    color = CENTER_COLORS.get(
        center_name,
        "#FFFFFF"
    )

    one = gpd.GeoDataFrame(
        [row],
        geometry="geometry",
        crs="EPSG:4326"
    )

    folium.GeoJson(

        one,

        style_function=lambda feature,
        c=color: {

            "fillColor": "transparent",
            "fillOpacity": 0,

            "color": c,
            "weight": 4,
            "opacity": 0.95,

            "interactive": False
        }

    ).add_to(
        center_group
    )


center_group.add_to(m)


# ============================================================
# 13. 센터 이름
# ============================================================

center_name_group = folium.FeatureGroup(
    name="119안전센터 이름",
    show=True
)


for _, row in center_boundary.iterrows():

    p = row.geometry.representative_point()

    center_name = row[
        "관할119안전센터"
    ]

    color = CENTER_COLORS.get(
        center_name,
        "#FFFFFF"
    )

    html = f"""
    <div style="
        background:rgba(0,0,0,0.72);
        color:white;
        border:2px solid {color};
        border-radius:6px;
        padding:4px 7px;
        font-family:'Malgun Gothic';
        font-size:11px;
        font-weight:bold;
        white-space:nowrap;
        pointer-events:none;
    ">
        {center_name}
    </div>
    """

    folium.Marker(

        location=[
            p.y,
            p.x
        ],

        icon=folium.DivIcon(
            html=html,
            icon_size=(150, 28),
            icon_anchor=(75, 14)
        ),

        interactive=False

    ).add_to(
        center_name_group
    )


center_name_group.add_to(m)


# ============================================================
# 14. 값 정리 함수
# ============================================================

def clean(v):

    if pd.isna(v):
        return "-"

    if isinstance(v, float):

        if v.is_integer():
            return str(int(v))

        return f"{v:.1f}"

    return str(v)


# ============================================================
# 15. 선정근거
# ============================================================

def make_reason(row):

    reasons = []

    if row["지역구분"] == "시내권 신고지점":

        reasons.append(
            "최근 3개년 실제 침수 신고"
        )

    else:

        reasons.append(
            "농촌 생활권 대표지점"
        )


    hand = row["HAND_m"]

    if pd.notna(hand):

        if hand <= 3:
            reasons.append(
                "HAND 3m 이하"
            )

        elif hand <= 5:
            reasons.append(
                "HAND 3~5m"
            )

        elif hand <= 10:
            reasons.append(
                "HAND 5~10m"
            )


    stream = row["잠재수로거리_m"]

    if pd.notna(stream):

        if stream <= 100:
            reasons.append(
                "잠재수로 100m 이내"
            )

        elif stream <= 300:
            reasons.append(
                "잠재수로 100~300m"
            )

        elif stream <= 500:
            reasons.append(
                "잠재수로 300~500m"
            )


    return " / ".join(
        reasons
    )


# ============================================================
# 16. 팝업 함수
# ============================================================

def make_popup(row, color):

    if row["지역구분"] == "농촌마을":

        type_text = (
            "농촌마을 대표지점"
        )

    else:

        type_text = (
            "시내권 실제 침수 신고지점"
        )


    popup_html = f"""

    <div style="
        width:365px;
        font-family:'Malgun Gothic';
        font-size:13px;
        line-height:1.65;
    ">


        <div style="
            font-size:17px;
            font-weight:bold;
        ">
            {clean(row['지점명'])}
        </div>


        <div style="
            color:#666;
            font-size:12px;
            margin-bottom:7px;
        ">
            {type_text}
        </div>


        <div style="
            display:inline-block;
            background:{color};
            color:white;
            padding:3px 9px;
            border-radius:5px;
            font-weight:bold;
            margin-bottom:8px;
        ">
            {clean(row['우려등급'])}
        </div>


        <hr style="
            border:none;
            border-top:1px solid #cccccc;
        ">


        <b>주소</b>

        <br>

        {clean(row['주소'])}


        <br><br>


        <div style="
            background:#E8F6F7;
            border-left:4px solid #00A6A6;
            padding:7px;
            border-radius:4px;
        ">

            <b>관할119안전센터</b>

            <br>

            {clean(row['관할119안전센터'])}

        </div>


        <br>


        <b>HAND</b> :
        {clean(row['HAND_m'])} m

        <br>


        <b>잠재수로 거리</b> :
        {clean(row['잠재수로거리_m'])} m


        <br><br>


        <b>최근 3개년 침수피해</b> :
        {clean(row['과거침수피해건수'])}건

        <br>


        <b>발생연도</b> :
        {clean(row['침수발생연도'])}

        <br>


        <b>피해유형</b> :
        {clean(row['피해유형'])}


        <br><br>


        <div style="
            background:#F4F4F4;
            padding:7px;
            border-radius:4px;
        ">

            <b>선정근거</b>

            <br>

            {make_reason(row)}

        </div>


        <br>


        <div style="
            color:#777;
            font-size:11px;
        ">

            ※ 침수위험 확정지점이 아닌
            지형·수로 및 과거 피해이력 기반
            침수우려지점

        </div>


    </div>
    """


    return folium.Popup(
        popup_html,
        max_width=420
    )


# ============================================================
# 17. 등급 레이어
# ============================================================

group_1 = folium.FeatureGroup(
    name=f"1순위 우려지점 ({count_1})",
    show=True
)

group_2 = folium.FeatureGroup(
    name=f"2순위 우려지점 ({count_2})",
    show=True
)


# ============================================================
# 18. 우려지점 표시
# ============================================================

for _, row in points.iterrows():

    grade = row[
        "우려등급"
    ]


    if grade == "1순위 우려지점":

        color = "#E31A1C"
        group = group_1
        radius = 7

    elif grade == "2순위 우려지점":

        color = "#FF9800"
        group = group_2
        radius = 6

    else:
        continue


    # 흰색 외곽
    folium.CircleMarker(

        location=[
            row["위도"],
            row["경도"]
        ],

        radius=radius + 2,

        color="#FFFFFF",

        weight=2,

        fill=True,

        fill_color="#FFFFFF",

        fill_opacity=0.90,

        interactive=False

    ).add_to(
        group
    )


    tooltip = (
        f"{clean(row['우려등급'])}"
        f" | "
        f"{clean(row['읍면'])}"
        f" | "
        f"{clean(row['관할119안전센터'])}"
    )


    folium.CircleMarker(

        location=[
            row["위도"],
            row["경도"]
        ],

        radius=radius,

        color="#222222",

        weight=1,

        fill=True,

        fill_color=color,

        fill_opacity=0.95,

        tooltip=tooltip,

        popup=make_popup(
            row,
            color
        )

    ).add_to(
        group
    )


group_2.add_to(m)
group_1.add_to(m)


# ============================================================
# 19. 안동시 전체 외곽선
# ============================================================

andong_union = (
    boundary.geometry
    .union_all()
)


andong_outline = gpd.GeoDataFrame(

    geometry=[
        andong_union
    ],

    crs="EPSG:4326"
)


folium.GeoJson(

    andong_outline,

    style_function=lambda feature: {

        "fillOpacity": 0,

        "color": "#FFFFFF",

        "weight": 3,

        "opacity": 1,

        "interactive": False

    }

).add_to(m)


# ============================================================
# 20. 화면 안동 전체에 맞춤
# ============================================================

margin_lat = (
    maxy - miny
) * 0.03

margin_lon = (
    maxx - minx
) * 0.03


m.fit_bounds(

    [

        [
            miny - margin_lat,
            minx - margin_lon
        ],

        [
            maxy + margin_lat,
            maxx + margin_lon
        ]

    ]

)


# ============================================================
# 21. 제목
# ============================================================

title_html = """

<div id="mapMainTitle" style="
    position:fixed;
    top:12px;
    left:50%;
    transform:translateX(-50%);
    z-index:9999;
    background:rgba(255,255,255,0.95);
    border:1px solid #555;
    border-radius:7px;
    padding:9px 18px;
    box-shadow:0 2px 6px rgba(0,0,0,0.25);
    font-family:'Malgun Gothic';
    font-size:18px;
    font-weight:bold;
    white-space:nowrap;
">

안동시 침수우려지점 분석지도

</div>

"""


m.get_root().html.add_child(
    folium.Element(
        title_html
    )
)


# ============================================================
# 22. 범례
# ============================================================

legend_html = f"""

<div id="floodLegend" style="
    position:fixed;
    bottom:30px;
    left:30px;
    z-index:9999;
    background:rgba(255,255,255,0.95);
    border:1px solid #666;
    border-radius:7px;
    padding:11px 14px;
    box-shadow:0 2px 6px rgba(0,0,0,0.20);
    font-family:'Malgun Gothic';
    font-size:13px;
">

<div style="
    font-weight:bold;
    font-size:14px;
    margin-bottom:7px;
">

침수우려지점

</div>


<span style="
    display:inline-block;
    width:12px;
    height:12px;
    border-radius:50%;
    background:#E31A1C;
    border:1px solid #222;
    margin-right:6px;
">
</span>

1순위 우려지점 ({count_1})

<br>


<span style="
    display:inline-block;
    width:12px;
    height:12px;
    border-radius:50%;
    background:#FF9800;
    border:1px solid #222;
    margin-right:6px;
">
</span>

2순위 우려지점 ({count_2})


<br><br>


<div style="
    color:#666;
    font-size:11px;
    line-height:1.55;
">

농촌 : 마을회관·경로당 대표지점

<br>

시내 : 최근 3개년 실제 침수 신고지점

<br>

HAND·잠재수로 및 과거 피해이력 반영

<br>

지점 클릭 시 상세정보 확인

</div>

</div>

"""


m.get_root().html.add_child(
    folium.Element(
        legend_html
    )
)

# ============================================================
# 강우현황 실측 패널
# 안동시 공식 강우량 페이지
# ============================================================

from datetime import datetime, timedelta
from io import StringIO
import requests
import json
import re


# ------------------------------------------------------------
# 1. 안동시 강우량 페이지
# ------------------------------------------------------------

RAIN_URL = (
    "https://www.andong.go.kr/portal/rainFall/list.do"
    "?mId=0609080000"
)


# ------------------------------------------------------------
# 2. 날짜별 강우자료 읽기
# ------------------------------------------------------------

def flatten_columns(df):

    cols = []

    for col in df.columns:

        if isinstance(col, tuple):

            parts = [
                str(x).strip()
                for x in col
                if str(x).strip().lower() != "nan"
            ]

            col_name = parts[-1] if parts else ""

        else:
            col_name = str(col).strip()

        cols.append(col_name)

    df.columns = cols

    return df


def find_rain_table(tables):

    for df in tables:

        temp = flatten_columns(df.copy())

        hour_count = 0

        for h in range(24):

            h1 = f"{h:02d}"
            h2 = str(h)

            if h1 in temp.columns or h2 in temp.columns:
                hour_count += 1

        if hour_count >= 20:
            return temp

    return None


def get_daily_rain(target_date):

    payload = {
        "searchType": "D",
        "searchYear": target_date.strftime("%Y"),
        "searchMonth": target_date.strftime("%m"),
        "searchDay": target_date.strftime("%d"),
    }

    print(
        "   강우 조회:",
        target_date.strftime("%Y-%m-%d")
    )

    response = requests.post(
        RAIN_URL,
        data=payload,
        timeout=30
    )

    response.raise_for_status()

    # 안동시 홈페이지 한글 인코딩
    response.encoding = response.apparent_encoding

    tables = pd.read_html(
        StringIO(response.text)
    )

    rain_table = find_rain_table(tables)

    if rain_table is None:
        raise RuntimeError(
            f"{target_date:%Y-%m-%d} 강우량 표를 찾지 못했습니다."
        )

    return rain_table


# ------------------------------------------------------------
# 3. 일별 표 → 시간별 자료 변환
# ------------------------------------------------------------

def daily_table_to_hourly(df, target_date):

    result = []

    area_col = df.columns[0]

    for _, row in df.iterrows():

        station = str(row[area_col]).strip()

        if (
            station == ""
            or station.lower() == "nan"
            or "평균" in station
            or "최대" in station
        ):
            continue

        for hour in range(24):

            col = None

            candidates = [
                f"{hour:02d}",
                str(hour)
            ]

            for candidate in candidates:

                if candidate in df.columns:
                    col = candidate
                    break

            if col is None:
                continue

            value = row[col]

            if pd.isna(value):
                continue

            text = str(value).strip()

            if text in [
                "",
                "-",
                "nan",
                "None"
            ]:
                continue

            # 숫자 외 문자 제거
            text = re.sub(
                r"[^0-9.\-]",
                "",
                text
            )

            if text == "":
                continue

            try:
                rain = float(text)
            except:
                continue

            dt = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour
            )

            result.append({
                "관측지점": station,
                "시각": dt,
                "강우량_mm": rain
            })

    return result


# ------------------------------------------------------------
# 4. 최근 4일 자료 수집
#
# 72시간 누적을 첫 실행부터 계산하기 위해
# 오늘 + 이전 3일 자료 사용
# ------------------------------------------------------------

print()
print("2. 안동시 실측 강우자료 수집 중...")


today = datetime.now().date()

rain_raw = []


for day_offset in range(4):

    target_date = (
        today
        - timedelta(days=day_offset)
    )

    try:

        daily_df = get_daily_rain(
            target_date
        )

        rain_raw.extend(
            daily_table_to_hourly(
                daily_df,
                target_date
            )
        )

    except Exception as e:

        print(
            f"   경고: {target_date} 조회 실패:",
            e
        )


if len(rain_raw) == 0:

    raise RuntimeError(
        "안동시 강우자료를 가져오지 못했습니다."
    )


rain_hourly = pd.DataFrame(
    rain_raw
)

rain_hourly["시각"] = pd.to_datetime(
    rain_hourly["시각"]
)

rain_hourly["강우량_mm"] = pd.to_numeric(
    rain_hourly["강우량_mm"],
    errors="coerce"
)

rain_hourly = rain_hourly.dropna(
    subset=[
        "관측지점",
        "시각",
        "강우량_mm"
    ]
)

rain_hourly = (
    rain_hourly
    .drop_duplicates(
        subset=[
            "관측지점",
            "시각"
        ],
        keep="last"
    )
    .sort_values(
        [
            "관측지점",
            "시각"
        ]
    )
)


# ------------------------------------------------------------
# 5. 최근 누적강우량 계산
# ------------------------------------------------------------

RAIN_PERIODS = [
    1,
    3,
    6,
    12,
    24,
    48,
    72
]


def rolling_rain(
    station_df,
    hours
):

    station_df = (
        station_df
        .sort_values("시각")
        .copy()
    )

    if len(station_df) == 0:
        return None

    end_time = station_df[
        "시각"
    ].max()

    start_time = (
        end_time
        - timedelta(
            hours=hours - 1
        )
    )

    x = station_df[
        (
            station_df["시각"]
            >= start_time
        )
        &
        (
            station_df["시각"]
            <= end_time
        )
    ]

    # 해당 시간 수만큼 자료가 있어야 계산
    if len(x) < hours:
        return None

    return round(
        x["강우량_mm"].sum(),
        1
    )


station_results = {}


for station in sorted(
    rain_hourly["관측지점"].unique()
):

    sdf = rain_hourly[
        rain_hourly["관측지점"]
        == station
    ]

    latest_time = sdf[
        "시각"
    ].max()

    values = {}

    for period in RAIN_PERIODS:

        values[period] = rolling_rain(
            sdf,
            period
        )

    station_results[station] = {
        "기준시각": latest_time,
        "강우": values
    }


# ------------------------------------------------------------
# 6. 읍면 → 실제 관측지점 연결
#
# 보조관측지점이 있는 지역은
# 해당 시간 누적값 중 최대값 표시
# ------------------------------------------------------------

RAIN_STATIONS = {

    "남후면": [
        "남후면"
    ],

    "일직면": [
        "일직면"
    ],

    "남선면": [
        "남선면"
    ],

    "길안면": [
        "길안면",
        "길안 대사"
    ],

    "임하면": [
        "임하면",
        "임하 신덕"
    ],

    "임동면": [
        "임동면",
        "[임동]-대곡2리"
    ],

    "풍산읍": [
        "풍산읍"
    ],

    "풍천면": [
        "풍천면",
        "풍천 어담",
        "[풍천]-구호교"
    ],

    "북후면": [
        "북후면",
        "[북후]-신전리"
    ],

    "서후면": [
        "서후면"
    ],

    "와룡면": [
        "와룡면"
    ],

    "도산면": [
        "도산면",
        "도산 단천",
        "[도산]-태자리"
    ],

    "예안면": [
        "예안면",
        "예안 삼계"
    ],

    "녹전면": [
        "녹전면"
    ]
}


# ------------------------------------------------------------
# 7. 시내 관측값 적용 지역
# ------------------------------------------------------------

URBAN_AREAS = [
    "중구동",
    "명륜동",
    "태화동",
    "평화동",
    "안기동",
    "서구동",
    "강남동",
    "용상동",
    "옥동",
    "송하동"
]


# ------------------------------------------------------------
# 8. 지역별 강우값 만들기
# ------------------------------------------------------------

def get_area_rain(
    area,
    period
):

    # 시내 동 지역
    if area in URBAN_AREAS:

        stations = [
            "시내"
        ]

    else:

        stations = RAIN_STATIONS.get(
            area,
            []
        )

    values = []

    for station in stations:

        info = station_results.get(
            station
        )

        if info is None:
            continue

        value = info[
            "강우"
        ].get(period)

        if value is not None:
            values.append(value)

    if not values:
        return None

    # 보조관측소 포함 최대값
    return max(values)


# ------------------------------------------------------------
# 9. 읍면동 → 안전센터
# ------------------------------------------------------------

def rain_center(area):

    return AREA_TO_CENTER.get(
        area,
        "미분류"
    )


# ------------------------------------------------------------
# 10. 강우자료 기준시각
# ------------------------------------------------------------

latest_times = [
    info["기준시각"]
    for info in station_results.values()
    if info["기준시각"] is not None
]


if latest_times:

    rain_reference_time = max(
        latest_times
    )

    rain_time = (
        rain_reference_time
        .strftime(
            "%Y.%m.%d %H:%M"
        )
    )

else:

    rain_time = "확인불가"


print(
    "   강우자료 기준시각:",
    rain_time
)


# ------------------------------------------------------------
# 11. 강우량 셀 표시
#
# 색상은 강우량 크기 확인용일 뿐
# 호우특보 / 침수위험등급 아님
# ------------------------------------------------------------

def rain_cell(value):

    if value is None:

        return """
        <td style="
            text-align:center;
            padding:5px 7px;
            background:#eeeeee;
            color:#777777;
            border-bottom:1px solid #dddddd;
        ">
            -
        </td>
        """

    if value >= 90:

        bg = "#D73027"
        fg = "#FFFFFF"

    elif value >= 60:

        bg = "#FC8D59"
        fg = "#000000"

    elif value >= 30:

        bg = "#FEE08B"
        fg = "#000000"

    else:

        bg = "#FFFFFF"
        fg = "#222222"

    if float(value).is_integer():
        display_value = int(value)
    else:
        display_value = value

    return f"""
        <td style="
            text-align:center;
            padding:5px 7px;
            background:{bg};
            color:{fg};
            border-bottom:1px solid #dddddd;
            font-weight:bold;
        ">
            {display_value}
        </td>
    """


# ------------------------------------------------------------
# 12. 안전센터 표시 순서
# ------------------------------------------------------------

CENTER_ORDER = [

    "법흥119안전센터",
    "용상119안전센터",
    "풍산119안전센터",
    "옥동119안전센터",
    "도산119안전센터"

]


# ------------------------------------------------------------
# 13. 읍면동 지도 이동 정보
# ------------------------------------------------------------

area_map_info = {}


for _, area_row in boundary.iterrows():

    area_name = area_row[
        "ADM_NM"
    ]

    if pd.isna(area_name):
        continue

    geom_area = area_row.geometry

    if (
        geom_area is None
        or geom_area.is_empty
    ):
        continue

    p = (
        geom_area
        .representative_point()
    )

    one_area = gpd.GeoDataFrame(
        [area_row],
        geometry="geometry",
        crs="EPSG:4326"
    )

    area_geojson = (
        one_area
        .__geo_interface__
    )

    area_map_info[
        str(area_name)
    ] = {

        "lat": float(p.y),
        "lon": float(p.x),
        "geojson": area_geojson

    }


# ------------------------------------------------------------
# 14. 강우현황 테이블 생성
# ------------------------------------------------------------

rain_rows = ""


for center in CENTER_ORDER:

    areas = CENTER_AREAS.get(
        center,
        []
    )

    if not areas:
        continue

    rain_rows += f"""

        <tr>

            <td colspan="8"
                style="
                    background:#333333;
                    color:white;
                    padding:5px 7px;
                    font-weight:bold;
                    font-size:12px;
                ">

                {center}

            </td>

        </tr>

    """


    for area in areas:

        values = {
            period:
            get_area_rain(
                area,
                period
            )
            for period
            in RAIN_PERIODS
        }


        rain_rows += f"""

        <tr>

            <td style="
                padding:3px 5px;
                white-space:nowrap;
                border-bottom:1px solid #dddddd;
            ">

                <button
                    type="button"
                    onclick="moveToArea('{area}')"
                    style="
                        border:none;
                        background:transparent;
                        color:#1565C0;
                        font-family:'Malgun Gothic';
                        font-size:11px;
                        font-weight:bold;
                        cursor:pointer;
                        padding:3px 4px;
                        text-decoration:underline;
                    "
                    title="{area} 지도 이동"
                >
                    {area}
                </button>

            </td>

            {rain_cell(values[1])}
            {rain_cell(values[3])}
            {rain_cell(values[6])}
            {rain_cell(values[12])}
            {rain_cell(values[24])}
            {rain_cell(values[48])}
            {rain_cell(values[72])}

        </tr>

        """


# ------------------------------------------------------------
# 15. 강우현황 패널
# ------------------------------------------------------------

area_map_json = json.dumps(
    area_map_info,
    ensure_ascii=False
)


rain_panel_html = f"""

<style>

#rainToggleButton {{

    position:fixed;
    top:180px;
    right:10px;

    z-index:10000;

    background:#1565C0;
    color:white;

    border:2px solid white;
    border-radius:6px;

    padding:8px 13px;

    font-family:'Malgun Gothic';
    font-size:13px;
    font-weight:bold;

    cursor:pointer;

    box-shadow:
        0 2px 6px
        rgba(0,0,0,0.35);
}}


#rainPanel {{

    position:fixed;

    top:210px;
    right:10px;

    width:610px;
    max-height:72vh;

    overflow-y:auto;
    overflow-x:auto;

    z-index:9999;

    display:none;

    background:
        rgba(
            255,
            255,
            255,
            0.97
        );

    border:1px solid #555;
    border-radius:8px;

    box-shadow:
        0 3px 10px
        rgba(0,0,0,0.35);

    font-family:'Malgun Gothic';
}}


#rainPanel table {{

    width:100%;

    border-collapse:
        collapse;

    font-size:11px;
}}


#rainPanel th {{

    position:sticky;

    top:0;

    background:#E3F2FD;

    padding:6px 5px;

    border-bottom:
        2px solid #777;

    text-align:center;

    z-index:2;
}}

</style>


<button
    id="rainToggleButton"
    onclick="toggleRainPanel()"
>

☔ 강우현황

</button>


<div id="rainPanel">

    <div style="
        padding:12px 13px 8px 13px;
    ">

        <div style="
            font-size:16px;
            font-weight:bold;
            margin-bottom:4px;
        ">

            안동시 실측 강우현황

        </div>


        <div style="
            font-size:11px;
            color:#555;
            margin-bottom:7px;
        ">

            강우자료 기준시각 :
            {rain_time}

        </div>


        <div style="
            background:#E8F4FD;
            border:1px solid #B6DDF2;
            color:#333333;
            padding:6px 8px;
            border-radius:4px;
            font-size:11px;
            line-height:1.5;
            margin-bottom:8px;
        ">

            ※ 안동시 강우량 관측자료를 이용한
            최근 누적강우량입니다.<br>

            ※ 읍·면 내 보조 관측지점이 있는 경우
            해당 시간대 누적강우량 중 최대값을 표시합니다.<br>

            ※ 시내 동 지역은 안동시 강우관측의
            '시내' 값을 공통 적용합니다.

        </div>


        <div style="
            font-size:11px;
            color:#555;
            margin-bottom:8px;
        ">

            단위 : mm /
            기준시각 이전 최근 누적강우량

        </div>


        <table>

            <thead>

                <tr>

                    <th>지역</th>
                    <th>1h</th>
                    <th>3h</th>
                    <th>6h</th>
                    <th>12h</th>
                    <th>24h</th>
                    <th>48h</th>
                    <th>72h</th>

                </tr>

            </thead>


            <tbody>

                {rain_rows}

            </tbody>

        </table>


        <div style="
            margin-top:9px;
            padding-top:7px;
            border-top:1px solid #cccccc;
            color:#666;
            font-size:10px;
            line-height:1.5;
        ">

            ※ 셀 색상은 강수량의 상대적 크기를
            쉽게 확인하기 위한 화면 표현이며
            호우특보 또는 침수위험 등급을
            의미하지 않습니다.<br>

            ※ 안동시 강우관측자료는
            재난상황 관리를 위한 참고자료입니다.

        </div>

    </div>

</div>


<script>

var areaMapInfo =
    {area_map_json};

var selectedAreaLayer =
    null;


// 강우현황 열기 / 닫기
function toggleRainPanel() {{

    var panel =
        document.getElementById(
            "rainPanel"
        );

    if (
        panel.style.display
            === "none"
        ||
        panel.style.display
            === ""
    ) {{

        panel.style.display =
            "block";

    }} else {{

        panel.style.display =
            "none";

    }}
}}


// 읍면동 클릭
// → 해당 지역 이동 + 경계 강조
function moveToArea(areaName) {{

    var info =
        areaMapInfo[areaName];

    if (!info) {{

        alert(
            areaName +
            "의 행정경계 정보를 찾을 수 없습니다."
        );

        return;
    }}


    var mapObject =
        {m.get_name()};


    mapObject.flyTo(
        [
            info.lat,
            info.lon
        ],
        13,
        {{
            animate:true,
            duration:0.8
        }}
    );


    if (
        selectedAreaLayer
        !== null
    ) {{

        mapObject.removeLayer(
            selectedAreaLayer
        );

        selectedAreaLayer =
            null;
    }}


    selectedAreaLayer =
        L.geoJSON(
            info.geojson,
            {{
                style:
                    function(feature) {{

                        return {{

                            color:
                                "#00FFFF",

                            weight:6,

                            opacity:1,

                            fillColor:
                                "#00FFFF",

                            fillOpacity:
                                0.10
                        }};
                    }},

                interactive:false
            }}
        );


    selectedAreaLayer.addTo(
        mapObject
    );


    setTimeout(
        function() {{

            if (
                selectedAreaLayer
                !== null
            ) {{

                selectedAreaLayer
                    .setStyle(
                    {{

                        color:
                            "#00FFFF",

                        weight:4,

                        opacity:0.85,

                        fillOpacity:0.03

                    }}
                );
            }}
        }},

        5000
    );
}}

</script>

"""


m.get_root().html.add_child(
    folium.Element(
        rain_panel_html
    )
)

# ============================================================
# 기상청 호우특보 표시
# warning.json은 별도 5분 자동화에서 갱신
# ============================================================

warning_panel_html = """
<style>

#kmaWarningPanel {
    position:fixed;
    top:65px;
    left:50%;
    transform:translateX(-50%);
    z-index:10001;

    display:none;

    min-width:260px;
    max-width:420px;

    background:rgba(190, 0, 0, 0.96);
    color:white;

    border:2px solid white;
    border-radius:8px;

    padding:9px 14px;

    box-shadow:
        0 3px 10px
        rgba(0,0,0,0.40);

    font-family:'Malgun Gothic';
    text-align:center;
}

#kmaWarningTitle {
    font-size:15px;
    font-weight:bold;
    margin-bottom:3px;
}

#kmaWarningLevel {
    font-size:17px;
    font-weight:bold;
}

#kmaWarningInfo {
    margin-top:4px;
    font-size:11px;
    line-height:1.5;
}

@media screen and (max-width:768px) {

    #kmaWarningPanel {
        top:12px;
        left:50%;
        right:auto;
        bottom:auto;
        transform:translateX(-50%);

        min-width:0;
        width:auto;
        max-width:90vw;

        padding:7px 12px;
        border-radius:7px;

        white-space:nowrap;
    }

    #kmaWarningTitle {
        display:none;
    }

    #kmaWarningLevel {
        font-size:14px;
        margin:0;
    }

    #kmaWarningInfo {
        font-size:9px;
        margin-top:2px;
    }
}

</style>


<div id="kmaWarningPanel">

    <div id="kmaWarningTitle">
        ⚠ 기상청 기상특보
    </div>

    <div id="kmaWarningLevel">
    </div>

    <div id="kmaWarningInfo">
    </div>

</div>


<script>

function loadKmaWarning() {

    fetch(
        "warning.json?t=" + Date.now()
    )

    .then(function(response) {

        if (!response.ok) {
            throw new Error(
                "warning.json 불러오기 실패"
            );
        }

        return response.json();

    })

    .then(function(data) {

        var panel =
            document.getElementById(
                "kmaWarningPanel"
            );

        var level =
            document.getElementById(
                "kmaWarningLevel"
            );

        var info =
            document.getElementById(
                "kmaWarningInfo"
            );


        if (data.active === true) {

            panel.style.display =
                "block";

    // 모바일에서는 특보 발효 시 기존 지도 제목 숨김
    if (window.innerWidth <= 768) {

        var mapTitle =
            document.getElementById(
                "mapMainTitle"
            );

        if (mapTitle) {
            mapTitle.style.display = "none";
        }
    }

            level.innerText =
                data.level + " 발효 중";


            var infoText =
                "대상 : "
                + (data.area || "안동시");


            if (data.announce_time) {

                infoText +=
                    " | 발표 : "
                    + data.announce_time;
            }


            if (data.effective_time) {

                infoText +=
                    " | 발효 : "
                    + data.effective_time;
            }


            info.innerText =
                infoText;


            if (
                data.level
                === "호우경보"
            ) {

                panel.style.background =
                    "rgba(180, 0, 0, 0.97)";

            } else {

                panel.style.background =
                    "rgba(230, 110, 0, 0.97)";
            }

       } else {

    panel.style.display =
        "none";

    // 특보가 없으면 기존 지도 제목 다시 표시
    var mapTitle =
        document.getElementById(
            "mapMainTitle"
        );

    if (mapTitle) {
        mapTitle.style.display = "block";
    }
}

    })

    .catch(function(error) {

        console.log(
            "기상청 특보정보:",
            error
        );

    });
}


// 처음 접속할 때 확인
loadKmaWarning();


// 지도를 계속 열어둔 경우에도
// 1분마다 warning.json 재확인
setInterval(
    loadKmaWarning,
    60000
);

</script>
"""


m.get_root().html.add_child(
    folium.Element(
        warning_panel_html
    )
)

# ============================================================
# 모바일 화면 최적화
# ============================================================

mobile_css = """
<style>

@media screen and (max-width: 768px) {

    /* 침수우려지점 범례 */
    #floodLegend {
        left: 7px !important;
        bottom: 7px !important;
        padding: 6px 8px !important;
        font-size: 10px !important;
        max-width: 155px !important;
        border-radius: 5px !important;
    }

    #floodLegend div:first-child {
        font-size: 11px !important;
        margin-bottom: 4px !important;
    }

    /* 모바일에서는 범례의 긴 설명 숨김 */
    #floodLegend div:last-child {
        display: none !important;
    }

    #floodLegend span {
        width: 9px !important;
        height: 9px !important;
        margin-right: 4px !important;
    }


    /* 강우현황 버튼 */
    #rainToggleButton {
        right: 7px !important;
        padding: 7px 10px !important;
        font-size: 11px !important;
    }


    /* 강우현황 창 */
    #rainPanel {
        left: 5px !important;
        right: 5px !important;
        width: auto !important;
        max-width: none !important;
        max-height: 68vh !important;
        overflow-x: auto !important;
        overflow-y: auto !important;
    }


    /* 강우량 표 */
    #rainPanel table {
        min-width: 540px !important;
        font-size: 10px !important;
    }

    #rainPanel th,
    #rainPanel td {
        padding: 4px 3px !important;
        white-space: nowrap !important;
    }

}

</style>
"""

m.get_root().html.add_child(
    folium.Element(
        mobile_css
    )
)

# ============================================================
# 23. 레이어 선택
# ============================================================

folium.LayerControl(

    collapsed=False,

    position="topright"

).add_to(m)


# ============================================================
# 24. 저장
# ============================================================

print()
print("3. 지도 저장 중...")


m.save(
    OUT_FILE
)


print()
print("=" * 75)
print("완료!")
print("=" * 75)

print()
print(
    "1순위:",
    count_1
)

print(
    "2순위:",
    count_2
)

print(
    "전체:",
    len(points)
)

print()
print(
    "생성파일:",
    OUT_FILE
)