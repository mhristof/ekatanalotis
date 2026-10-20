import re

import net

SECTIONS = [
    "eidi-artozacharoplasteioy",
    "freska-froyta-lachanika",
    "fresko-psari-thalassina",
    "fresko-kreas",
    "galata-rofimata-chymoi-psygeioy",
    "giaoyrtia-kremes-galaktos-epidorpia-psygeioy",
    "turokomika-futika-anapliromata",
    "ayga-voytyro-nopes-zymes-zomoi",
    "allantika",
    "orektika-delicatessen",
    "etoima-geymata",
    "katepsygmena",
    "kava",
    "anapsyktika-nera-chymoi",
    "xiroi-karpoi-snak",
    "mpiskota-sokolates-zacharodi",
    "eidi-proinoy-rofimata",
    "vrefikes-paidikes-trofes",
    "trofima-pantopoleioy",
    "trofes-eidi-gia-katoikidia",
    "eidi-mias-chrisis-eidi-parti",
    "chartika-panes-servietes",
    "kallyntika-eidi-prosopikis-ygieinis",
    "aporrypantika-eidi-katharismoy",
    "eidi-oikiakis-chrisis",
]

PRODUCT = re.compile(
    r"data-plugin-analyticsimpressions=.*?{&quot;item_id&quot;:&quot;(\d+)&quot;,&quot;item_name&quot;:&quot;(.*?)&quot;.*?price&quot;:(\d+\.\d+)",
    re.DOTALL,
)


def parse(html_content):
    return [[code, name, float(price)] for code, name, price in PRODUCT.findall(html_content)]


def fetch_page(section, page):
    return parse(net.get_text(f"https://www.sklavenitis.gr/{section}/?pg={page}"))


def sklavenitis(sections=None, max_pages=None):
    return net.crawl("sklavenitis", sections or SECTIONS, fetch_page, max_pages)
