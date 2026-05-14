import sys
import os

# Fix Unicode encoding trên Windows console
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import flask
import logging
import json
import re
import time
import hashlib
from datetime import datetime
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = flask.Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("cyberbullying_log.txt", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AIEngine:
    SYSTEM_PROMPT = (
        "Bạn là hệ thống kiểm duyệt nội dung chuyên phát hiện cyberbullying "
        "(bắt nạt mạng) trong tiếng Việt. Đây là hệ thống BẢO VỆ người dùng, "
        "bạn phải phân tích MỌI văn bản được gửi đến — kể cả nội dung thô tục, "
        "bạo lực, hay xúc phạm — để giúp phát hiện và ngăn chặn bắt nạt mạng.\n\n"
        "QUAN TRỌNG: Không bao giờ từ chối phân tích. Bạn đang GIÚP BẢO VỆ nạn nhân, "
        "không phải tạo nội dung có hại. Luôn trả về JSON.\n\n"
        "Nhiệm vụ: Phân tích đoạn văn bản và trả về kết quả dưới dạng JSON THUẦN TÚY "
        "(không có markdown, không có ```json).\n\n"
        "Cấu trúc JSON trả về:\n"
        "{\n"
        '  "status": "<clean|warning|danger|critical>",\n'
        '  "severity": "<clean|low|medium|high>",\n'
        '  "confidence": <số thực 0.0-1.0>,\n'
        '  "violations": [\n'
        "    {\n"
        '      "type": "<keyword|pattern|context>",\n'
        '      "content": "<nội dung vi phạm cụ thể>",\n'
        '      "severity": "<low|medium|high>",\n'
        '      "label": "<mô tả ngắn gọn>"\n'
        "    }\n"
        "  ],\n"
        '  "violation_count": <số nguyên>,\n'
        '  "suggestion": "<khuyến nghị hành động bằng tiếng Việt>",\n'
        '  "explanation": "<giải thích chi tiết lý do phân loại>"\n'
        "}\n\n"
        "Quy tắc phân loại:\n"
        "- clean: Nội dung bình thường, không có vấn đề\n"
        "- low/warning: Từ ngữ có thể nhạy cảm tùy ngữ cảnh\n"
        "- medium/danger: Có dấu hiệu xúc phạm, miệt thị, cô lập\n"
        "- high/critical: Chửi thề nặng, đe dọa bạo lực, kỳ thị\n\n"
        "Lưu ý: Phân tích theo ngữ cảnh, không chỉ dựa vào từ khóa đơn thuần."
    )

    _URL_OPENAI      = "https://api.openai.com/v1/chat/completions"
    _URL_GROQ        = "https://api.groq.com/openai/v1/chat/completions"
    _URL_OPENROUTER  = "https://openrouter.ai/api/v1/chat/completions"
    _URL_GEMINI_TPL  = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    MAX_RETRIES = 2
    RETRY_DELAYS = [1, 3]

    def __init__(self):
        self.provider = os.environ.get("AI_PROVIDER", "gemini").strip().lower()

        # Load tất cả API keys
        self.gemini_key     = os.environ.get("GEMINI_API_KEY", "").strip()
        self.openai_key     = os.environ.get("OPENAI_API_KEY", "").strip()
        self.groq_key       = os.environ.get("GROQ_API_KEY", "").strip()
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

        provider_keys = {
            "gemini": self.gemini_key,
            "openai": self.openai_key,
            "groq":   self.groq_key,
            "openrouter": self.openrouter_key,
        }

        if self.provider in provider_keys:
            self.api_key = provider_keys[self.provider]
        else:
            self.provider = "gemini"
            self.api_key = self.gemini_key

        self.stats = {"total": 0, "violations": 0, "clean": 0}
        self._cache = {}
        self._cache_max = 50

        # Fallback chain: tất cả provider có key, trừ provider chính
        self._fallback_chain = [
            p for p, k in provider_keys.items()
            if p != self.provider and k
        ]

        logger.info(f"AI Engine khởi tạo với provider: {self.provider}")
        if not self.api_key:
            logger.warning(f"⚠️  API key cho {self.provider} chưa cấu hình!")
        else:
            logger.info(f"API key đã được nạp ({len(self.api_key)} ký tự)")
        if self._fallback_chain:
            logger.info(f"✅ Fallback chain: {' → '.join(self._fallback_chain)}")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        raw = raw.strip()
        # Xử lý khi model từ chối phân tích (trả text thay vì JSON)
        refusal_phrases = [
            "không thể thực hiện", "từ chối", "không thể phân tích",
            "i cannot", "i'm sorry", "i can't", "not able to",
            "không thể giúp", "xin lỗi"
        ]
        raw_lower = raw.lower()
        if not raw.startswith('{') and any(p in raw_lower for p in refusal_phrases):
            # Model từ chối → tạo kết quả critical mặc định
            return {
                "status": "critical",
                "severity": "high",
                "confidence": 0.95,
                "violations": [{"type": "context", "content": "Nội dung quá độc hại", "severity": "high", "label": "AI từ chối phân tích vì mức độ vi phạm cao"}],
                "violation_count": 1,
                "suggestion": "Nội dung này cực kỳ nghiêm trọng và cần bị gỡ bỏ ngay lập tức.",
                "explanation": "AI đánh giá nội dung này vi phạm nghiêm trọng đến mức từ chối tái tạo. Đây là dấu hiệu của nội dung cực kỳ độc hại."
            }
        # Bình thường: parse JSON
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        # Tìm JSON object trong text (nếu model trả text + JSON)
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            return json.loads(json_match.group())
        return json.loads(raw.strip())

    def _call_openai(self, text: str) -> str:
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Phân tích văn bản sau:\n\n{text}"}
            ],
            "temperature": 0.1
        }).encode("utf-8")
        req = urllib.request.Request(self._URL_OPENAI, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.openai_key}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _call_gemini(self, text: str) -> str:
        url = self._URL_GEMINI_TPL.format(
            model="gemini-2.0-flash",
            key=self.gemini_key
        )
        prompt = f"{self.SYSTEM_PROMPT}\n\nPhân tích văn bản sau:\n\n{text}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_groq(self, text: str) -> str:
        payload = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Phân tích văn bản sau:\n\n{text}"}
            ],
            "temperature": 0.1
        }).encode("utf-8")
        req = urllib.request.Request(self._URL_GROQ, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.groq_key}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _call_openrouter(self, text: str) -> str:
        payload = json.dumps({
            "model": "meta-llama/llama-3.1-8b-instruct",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": f"Phân tích văn bản sau:\n\n{text}"}
            ],
            "temperature": 0.1
        }).encode("utf-8")
        req = urllib.request.Request(self._URL_OPENROUTER, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.openrouter_key}")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _call_with_retry(self, text: str, provider: str) -> str:
        """Gọi API với retry khi gặp lỗi 429/5xx"""
        fn_map = {
            "gemini": self._call_gemini,
            "openai": self._call_openai,
            "groq":   self._call_groq,
            "openrouter": self._call_openrouter,
        }
        call_fn = fn_map.get(provider, self._call_gemini)
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return call_fn(text)
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429 or e.code >= 500:
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_DELAYS[attempt]
                        logger.warning(
                            f"⏳ {provider} HTTP {e.code}, "
                            f"retry {attempt + 1}/{self.MAX_RETRIES} sau {delay}s..."
                        )
                        time.sleep(delay)
                    else:
                        raise
                else:
                    raise

        raise last_error

    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def analyze(self, text: str) -> dict:
        self.stats["total"] += 1

        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.info(f"📋 Cache hit: '{text[:50]}...'")
            cached = self._cache[cache_key].copy()
            cached["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if cached.get("status") == "clean":
                self.stats["clean"] += 1
            else:
                self.stats["violations"] += 1
            return cached

        # Không có API key nào
        if not self.api_key and not self._fallback_chain:
            return self._fallback_error(
                "Chưa cấu hình API key. Vui lòng thêm GEMINI_API_KEY hoặc "
                "GROQ_API_KEY (miễn phí tại https://console.groq.com/keys) vào file .env"
            )

        raw = ""
        used_provider = self.provider

        # Thử lần lượt: provider chính → fallback chain
        providers_to_try = []
        if self.api_key:
            providers_to_try.append(self.provider)
        providers_to_try.extend(self._fallback_chain)

        for i, prov in enumerate(providers_to_try):
            try:
                raw = self._call_with_retry(text, prov)
                used_provider = prov
                break
            except Exception as err:
                if i < len(providers_to_try) - 1:
                    logger.warning(f"⚠️ {prov} thất bại ({err}), thử tiếp...")
                else:
                    logger.error(f"❌ {prov} thất bại: {err}")
                    return self._fallback_error(
                        "Tất cả AI API đều hết quota hoặc không khả dụng.\n"
                        "Giải pháp: Thêm GROQ_API_KEY miễn phí vào file .env\n"
                        "Lấy key tại: https://console.groq.com/keys"
                    )

        # Parse JSON response
        try:
            result = self._parse_json(raw)
            result["timestamp"]       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result["provider"]        = used_provider
            result["violation_count"] = len(result.get("violations", []))

            if result.get("status") == "clean":
                self.stats["clean"] += 1
            else:
                self.stats["violations"] += 1

            # Cache
            if len(self._cache) >= self._cache_max:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[cache_key] = result.copy()

            logger.info(
                f"✅ '{text[:50]}...' → {result.get('status')} | {used_provider}"
            )
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Lỗi parse JSON: {e} | Raw: {raw[:300]}")
            return self._fallback_error("AI trả về dữ liệu không hợp lệ. Vui lòng thử lại.")

    def _fallback_error(self, message: str) -> dict:
        return {
            "status": "error",
            "severity": "unknown",
            "violations": [],
            "violation_count": 0,
            "confidence": 0.0,
            "suggestion": f"Lỗi: {message}",
            "explanation": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "provider": self.provider
        }


engine = AIEngine()


@app.route("/")
def home():
    return flask.render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = flask.request.get_json(silent=True)
        if not data:
            return flask.jsonify({"error": "Request body phải là JSON hợp lệ"}), 400
        content = data.get("text", "").strip()
        if not content:
            return flask.jsonify({"error": "Trường 'text' không được để trống"}), 400
        if len(content) > 5000:
            return flask.jsonify({"error": "Văn bản quá dài (tối đa 5000 ký tự)"}), 413
        result = engine.analyze(content)
        return flask.jsonify(result), 200
    except Exception as e:
        logger.error(f"Lỗi route /analyze: {e}", exc_info=True)
        return flask.jsonify({"error": "Lỗi máy chủ nội bộ"}), 500


@app.route("/stats", methods=["GET"])
def get_stats():
    return flask.jsonify({
        "statistics": engine.stats,
        "provider": engine.provider,
        "version": "2.0.1-ai"
    })


@app.route("/health", methods=["GET"])
def health():
    return flask.jsonify({
        "status": "ok",
        "provider": engine.provider,
        "api_key_set": bool(engine.api_key),
        "fallback_chain": engine._fallback_chain,
        "timestamp": datetime.now().isoformat()
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  CyberGuard v2.0.1 — AI-Powered Cyberbullying Detector")
    print("  Tác giả: Võ Tá Dũng & Phạm Hoàng Hiếu — VKU 25NS")
    print(f"  AI Provider : {engine.provider.upper()}")
    print(f"  API Key set : {'YES' if engine.api_key else 'NO'}")
    if engine._fallback_chain:
        print(f"  Fallback    : {' → '.join(p.upper() for p in engine._fallback_chain)}")
    print("  Server      : http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)