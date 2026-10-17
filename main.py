import hmac, hashlib, requests, string, random, json, codecs, time, os
import base64
import urllib.parse
from datetime import datetime, timezone
from fastapi import FastAPI, Query
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import urllib3

urllib3.disable_warnings()

# ============================================================
# CONFIG & CONSTANTS
# ============================================================
AES_KEY = bytes([89,103,38,116,99,37,68,69,117,104,54,37,90,99,94,56])
AES_IV  = bytes([54,111,121,90,68,114,50,50,69,51,121,99,104,106,77,37])
REGION_LANG = {"ME":"ar","IND":"hi","ID":"id","VN":"vi","TH":"th","BD":"bn","PK":"ur","TW":"zh","CIS":"ru","SAC":"es","BR":"pt"}
HEX_KEY = bytes.fromhex("32656534343831396539623435393838343531343130363762323831363231383734643064356437616639643866376530306331653534373135623764316533")

FIELD_22 = bytes.fromhex(
    "4747524501010100620200001052aa0d669c6a368f08338060d2ee0690053af84a41edcd3558556ec10f24f4"
    "6c93ac64ca41a16732c46a2cb071246a79b8929032f9e1b6f4ef331bd53cabf29b09b97349a46e9863c0314e"
    "1a0d80819fef8aabf03876b3d037db354a7ccb5c1bce96411fb3753f6f50e44c69c4ed617fa30efb8ffc0517"
    "ff2f636739be1f304d999cfd6fd48bf69454199794c3dc88f55a4bdbd66534d5a061359cdfd1fb680cd37918"
    "df9fdb3cf7d80067b0a3506c90063cf62b2ccec11e23913a2fd7c4ef091331967bb518a5ad1e551146b90821"
    "be800883abadde39d6c80a5d798611466c748f075481806c5842ce45e6bd4e3368ec08fe2ec41ceb880cd862"
    "49eb71693f79f0bccf9e590c3fae12519fe08c7a1905d0927690109e0df28574bb14847225db1a59230e6662"
    "ed7730e15ff9a6c815cb41b420edeada735a4b03e181037c37c2c850257311df2f07b0a56e759372cbd0268e"
    "3f13a292ee4373e38ab5096e0342a5e0d7fec6da2bbc265d74baadd2b24ee4f74862f82c21d6694bac53f8ce"
    "80312a30068a6276a641c19b11d0305c6fe2f531ac7de578b29f543697f5c73663e6f23aa15277b6122dcd4d"
    "4171e38f9ac0b173f39c58416a16c5c1f4a35acd065ce78f449cf538a249339e763272d458e4ed86c976591a"
    "9c066b3a37111e44091eb6b5a795249f3e5145db022a6055f2cc675936391312f688f89627845df222a91156"
    "555225be36f9714a0ba50246d0f003bda3c9c1292ab73b4f79635ddd023218eda93a302d79e023404c143965"
    "44a930b98ed54771aca7fec10d095587685b473e81a9619764fad9256529dcd6e911f4f4629612287d4ee3ec"
    "5389f6ec4ec020b0e2aac017232a9197be9e46239ce690fe5d4872b2e98e651510c971667f3aca8b59f3e9d5"
    "0e43"
)

# ============================================================
# DEVICE & IP SPOOFER
# ============================================================
REGION_IP_PREFIX = {
    "ID":  ["103.","114.","118.","125.","180."],
    "IND": ["49.","103.","106.","115.","182."],
    "VN":  ["113.","115.","171.","203.","210."],
    "TH":  ["49.","101.","110.","171.","202."],
    "BD":  ["103.","114.","119.","202.","203."],
    "PK":  ["39.","111.","119.","175.","202."],
    "TW":  ["36.","39.","61.","111.","114."],
    "ME":  ["5.","37.","46.","94.","176."],
    "CIS": ["5.","31.","37.","46.","95."],
    "SAC": ["177.","179.","181.","186.","189."],
    "BR":  ["177.","179.","181.","186.","189."],
}

def get_spoofed_ip(region):
    prefixes = REGION_IP_PREFIX.get(region.upper(), REGION_IP_PREFIX["ID"])
    p = random.choice(prefixes)
    return f"{p}{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def get_random_device():
    models = [
        ("Asus ASUS_I005DA", "ARMv7 VFPv3 NEON VMH | 2400 | 2", "Adreno (TM) 640"),
        ("SM-A525F", "ARMv8 VFPv4 NEON VMH | 2200 | 8", "Adreno (TM) 618"),
        ("SM-S918B", "ARMv8 VFPv4 NEON VMH | 3200 | 8", "Adreno (TM) 740"),
        ("Redmi Note 10","ARMv8 VFPv4 NEON VMH | 2200 | 8","Adreno (TM) 619"),
        ("Poco X3","ARMv8 VFPv4 NEON VMH | 2300 | 8","Adreno (TM) 618"),
        ("Pixel 7 Pro","ARMv8 VFPv4 NEON VMH | 2800 | 8","Mali-G710"),
        ("OnePlus 11","ARMv8 VFPv4 NEON VMH | 3200 | 8","Adreno (TM) 740"),
    ]
    android_versions = [
        ("Android OS 11 / API-30 (RP1A.201005.001)","11","30"),
        ("Android OS 12 / API-31 (SP1A.210812.016)","12","31"),
        ("Android OS 13 / API-33 (TQ3A.230805.001)","13","33"),
        ("Android OS 14 / API-34 (UP1A.231005.007)","14","34"),
    ]
    model, cpu, gpu = random.choice(models)
    os_str, android_ver, api = random.choice(android_versions)
    uuid = f"{''.join(random.choices('0123456789abcdef', k=8))}-{''.join(random.choices('0123456789abcdef', k=4))}-{''.join(random.choices('0123456789abcdef', k=4))}-{''.join(random.choices('0123456789abcdef', k=4))}-{''.join(random.choices('0123456789abcdef', k=12))}"
    
    return {
        "model": model, "brand": model.split()[0], "cpu": cpu, "gpu": gpu,
        "android_full": os_str, "android_version": android_ver, "api_level": api,
        "uuid": uuid,
        "operator": random.choice(["Telkomsel","Indosat","XL Axiata","Airtel","Jio"]),
        "network": random.choice(["WIFI","4G","5G"]),
        "lang_code": random.choice(["en","in","hi","vi","th","pt","es"]),
    }

# ============================================================
# PROTOBUF & AES HELPERS
# ============================================================
def encode_varint(n):
    if n < 0: return b''
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n: b |= 0x80
        out.append(b)
        if not n: break
    return bytes(out)

def build_proto(fields):
    parts = []
    for k, v in fields.items():
        if isinstance(v, dict):
            nested = build_proto(v)
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(nested)) + nested)
        elif isinstance(v, int):
            parts.append(encode_varint((k << 3) | 0) + encode_varint(v))
        elif isinstance(v, (str, bytes)):
            ev = v.encode() if isinstance(v, str) else v
            parts.append(encode_varint((k << 3) | 2) + encode_varint(len(ev)) + ev)
    return b''.join(parts)

def aes_encrypt(hex_data):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(bytes.fromhex(hex_data), AES.block_size))

def encrypt_api(plain_hex):
    return AES.new(AES_KEY, AES.MODE_CBC, AES_IV).encrypt(pad(bytes.fromhex(plain_hex), AES.block_size)).hex()

def encode_f14(s):
    ks = [0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,
          0x30,0x30,0x30,0x30,0x30,0x32,0x30,0x31,0x37,0x30,0x30,0x30,0x30,0x30,0x32,0x30]
    return bytes(ord(c) ^ ks[i % len(ks)] for i, c in enumerate(s))

def generate_random_name(prefix):
    chars = string.ascii_letters + string.digits
    return prefix + ''.join(random.choice(chars) for _ in range(6)).upper()

# ============================================================
# CORE GARENA LOGIC
# ============================================================
def get_headers(region, device, extra=None):
    headers = {
        "User-Agent": "GarenaMSDK/4.0.42(SM-A525F ;Android)",
        "X-Forwarded-For": get_spoofed_ip(region),
        "X-Real-IP": get_spoofed_ip(region),
    }
    if extra:
        headers.update(extra)
    return headers

def create_account_direct(region, name_prefix, pass_prefix):
    session = requests.Session()
    try:
        # 1. Register Guest
        rand_part = "".join(random.choices("0123456789ABCDEF", k=16))
        password = f"{pass_prefix}_{rand_part}"
        url = "https://100067.connect.garena.com/api/v2/oauth/guest:register"
        payload = {"app_id": 100067, "client_type": 2, "password": password, "source": 2}
        body_json = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(HEX_KEY, body_json.encode("utf-8"), hashlib.sha256).hexdigest()
        
        dev = get_random_device()
        headers = get_headers(region, dev, {
            "Authorization": f"Signature {signature}",
            "Content-Type": "application/json; charset=utf-8",
            "Host": "100067.connect.garena.com"
        })
        
        resp = session.post(url, headers=headers, data=body_json, timeout=15, verify=False)
        if resp.status_code != 200 or "uid" not in resp.json().get("data", {}):
            return None
            
        uid = resp.json()["data"]["uid"]
        
        # 2. Get Token
        url_token = "https://100067.connect.garena.com/oauth/guest/token/grant"
        body_token = {"uid": uid, "password": password, "response_type": "token",
                      "client_type": "2", "client_secret": HEX_KEY, "client_id": "100067"}
        resp_token = session.post(url_token, headers=get_headers(region, dev), data=body_token, timeout=15, verify=False)
        
        if resp_token.status_code != 200 or 'open_id' not in resp_token.json():
            return None
            
        open_id = resp_token.json()['open_id']
        access_token = resp_token.json()["access_token"]
        
        # 3. Major Register
        name = generate_random_name(name_prefix)
        url_reg = "https://loginbp.ppmainecoonghj.com/MajorRegister" if region.upper() not in ["ME","TH"] else "https://loginbp.common.ggbluefox.com/MajorRegister"
        lang = REGION_LANG.get(region.upper(), "en")
        
        reg_msg = {1: name, 2: access_token, 3: open_id, 5: 102000007, 6: 4, 7: 1, 13: 1,
                   14: encode_f14(open_id), 15: lang, 16: 2, 20: "2.132.4", 21: 1, 22: FIELD_22}
        payload_bytes = build_proto(reg_msg)
        encrypted = aes_encrypt(payload_bytes.hex())
        
        headers_reg = get_headers(region, dev, {
            'Host': 'loginbp.ppmainecoonghj.com',
            'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Authorization': 'Bearer',
            'X-GA': 'v1 1',
            'ReleaseVersion': "OB55",
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        
        session.post(url_reg, headers=headers_reg, data=encrypted, timeout=15, verify=False)
        
        # 4. Major Login
        gpu = dev["gpu"]
        gpu_full = f"{gpu}|OpenGL ES 3.2"
        ip_addr = get_spoofed_ip(region)
        
        payload_dict = {
            3: datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            4: b'free fire', 5: 1, 7: "2.132.4", 8: dev["android_full"],
            9: b'Handheld', 10: dev["operator"], 11: dev["network"],
            12: 1280, 13: 720, 14: b'240', 15: dev["cpu"],
            16: random.choice([5951, 6000, 6100, 5500]),
            17: gpu, 18: gpu_full,
            19: f'Google|{dev["uuid"]}', 20: ip_addr, 21: lang,
            22: open_id.encode(), 23: b'4', 24: b'Handheld',
            25: dev["model"], 26: lang, 29: access_token.encode(), 30: 1,
            41: dev["operator"], 42: dev["network"],
            57: b'1ac4b80ecf0478a44203bf8fac6120f5',
            60: 30000, 61: 30000, 62: 2519, 63: 243,
            64: 32357, 65: 34308, 66: 32357, 67: 34308, 73: 1,
            74: b'/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/lib/arm',
            76: 2,
            77: b'428775ab8c8845bd341b5357ec61d15e|/data/app/~~iw-K-GR3srU7dLE-UxJ4bg==/com.dts.freefiremax-kbPhw3SUYautW0I_oayB_A==/base.apk',
            78: 2, 79: 1, 81: b'32', 83: b'2019118525', 85: 3,
            86: b'OpenGLES3', 87: 4095, 88: 4,
            92: random.choice([19788, 20000, 21000]),
            93: b'android_max',
            94: b'KqsHT2gyPt7vUCc9SCjv2ioi3WEZSEL86ErvXB38suVVK/Z4IVt78ESl/r2S15C1pqu/j6ZmgFL7HbwoFiiVconX08ooKiisQffvEAPCo/C+Lahr',
            96: b'{"cur_rate":null,"support_etc2":true}',
            97: 1, 98: 1, 99: b'4', 100: b'4', 102: b'',
            104: 77149, 105: 1,
            106: b'https://dl.cdn.freefiremobile.com/live/ABHotUpdates/|https://dl-core.cdn.freefiremobile.com/live/ABHotUpdates/|6b2078db9d22dd98f8e9386a39af8462',
            107: b'c8e41b7a93f02d56e1a94c7b8203f5d1',
        }
        data = build_proto(payload_dict)
        url_login = "https://loginbp.ppmainecoonghj.com/MajorLogin" if region.upper() not in ["ME", "TH"] else "https://loginbp.common.ggbluefox.com/MajorLogin"
        
        headers_login = get_headers(region, dev, {
            'Host': 'loginbp.ppmainecoonghj.com',
            'User-Agent': 'UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)',
            'Authorization': 'Bearer', 'X-GA': 'v1 1',
            'X-Ga-Sv': '1789534056',
            'ReleaseVersion': "OB55",
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        
        enc_hex = encrypt_api(data.hex())
        resp_login = session.post(url_login, headers=headers_login, data=bytes.fromhex(enc_hex), timeout=15, verify=False)
        
        account_id = "N/A"
        jwt_token = ""
        
        if resp_login.status_code == 200 and len(resp_login.text) > 10:
            jwt_start = resp_login.text.find("eyJ")
            if jwt_start != -1:
                jwt_token = resp_login.text[jwt_start:]
                second_dot = jwt_token.find(".", jwt_token.find(".") + 1)
                if second_dot != -1:
                    jwt_token = jwt_token[:second_dot + 44]
                    try:
                        parts = jwt_token.split('.')
                        if len(parts) >= 2:
                            pp = parts[1]
                            padding = 4 - len(pp) % 4
                            if padding != 4: pp += '=' * padding
                            claims = json.loads(base64.urlsafe_b64decode(pp))
                            account_id = claims.get('account_id') or claims.get('external_id')
                    except: pass
                    
        if account_id and str(account_id) != "N/A":
            return {
                "uid": str(uid), "password": password, "name": name, "region": region,
                "account_id": str(account_id), "jwt_token": jwt_token,
                "device_model": dev["model"], "device_id": dev["uuid"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "_source": "DIRECT",
            }
        return None
    except Exception as e:
        print(f"Error generating: {e}")
        return None
    finally:
        session.close()

def analyze_pattern(account_id):
    if not account_id or account_id == "N/A" or not str(account_id).isdigit(): return "", 0
    freq = {}
    for d in str(account_id): freq[d] = freq.get(d, 0) + 1
    best_digit, best_count = None, 0
    for digit, count in freq.items():
        if count > best_count: best_digit, best_count = digit, count
    if best_count >= 4: return f"{best_digit}×{best_count}", best_count * 3
    return "", 0

def get_tier_name(score):
    if score >= 30: return "MYTHIC"
    if score >= 21: return "LEGENDARY"
    if score >= 15: return "EPIC"
    if score >= 12: return "RARE"
    return "COMMON"

# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(title="KynSt Gen API")

@app.get("/")
def read_root():
    return {"status": True, "message": "KynSt Generator API is running!", "version": "1.0.0"}

@app.get("/api/v2/gen")
def generate_account(
    region: str = Query("ID", description="Region code (ID, IND, VN, TH, BD, PK, TW, ME, CIS, SAC, BR)"),
    count: int = Query(1, description="Number of accounts to generate (max 10)"),
    threshold: int = Query(11, description="Rarity threshold"),
    name: str = Query("KynSt", description="Name prefix"),
    password_prefix: str = Query("KynSt", description="Password prefix"),
    ghost: int = Query(0, description="Ghost mode")
):
    valid_regions = ["ID", "IND", "VN", "TH", "BD", "PK", "TW", "ME", "CIS", "SAC", "BR"]
    region = region.upper()
    if region not in valid_regions:
        region = "ID"
        
    count = min(max(1, count), 10) # Limit max 10 per request biar gak timeout di Railway
    
    results = []
    for _ in range(count):
        acc = create_account_direct(region, name, password_prefix)
        if acc:
            detail, score = analyze_pattern(acc["account_id"])
            tier = get_tier_name(score)
            acc["score"] = score
            acc["tier"] = tier
            acc["is_rare"] = score > threshold
            acc["pattern"] = detail
            results.append(acc)
            
    if not results:
        return {"status": False, "message": "Gagal generate akun. Coba lagi.", "results": []}
        
    return {"status": True, "count": len(results), "results": results}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)