"""
Language Detection & Contextual Interpretability Module

Implements:
1. Three explicit language states:
   - 'english'
   - 'non_english'
   - 'uncertain'
2. Context-aware evaluation:
   - Uses target customer message and allowed prior ancestor turns (including prior brand questions).
   - Excludes selected future brand reply (changing future reply cannot alter decisions).
   - Preserves understandable short follow-ups ("Yes", "Android", "Still broken") when preceding turns explain them.
   - Prohibits English ancestors from overriding clearly non-English targets.
3. Language heuristic scoring:
   - Named `language_heuristic_score` (rule-based heuristic, not calibrated probability).
   - Treats missing stopwords / technical terms ("Connection refused") and Latin character gibberish as uncertain, rather than misclassifying them.
4. Human review queue and verification sheet preparation.
"""

import re
import csv
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
from src.sample_brand_conversations import redact_sensitive_info

LANGUAGE_STATE_ENGLISH = "english"
LANGUAGE_STATE_NON_ENGLISH = "non_english"
LANGUAGE_STATE_UNCERTAIN = "uncertain"

ENGLISH_STOPWORDS: Set[str] = {
    'the', 'i', 'to', 'a', 'and', 'is', 'in', 'it', 'you', 'that', 'of', 'for', 'on', 'are',
    'with', 'as', 'at', 'be', 'this', 'have', 'from', 'my', 'me', 'not', 'can', 'help', 'please',
    'why', 'does', 'app', 'play', 'playlist', 'account', 'music', 'listening', 'offline', 'update',
    'song', 'songs', 'working', 'phone', 'device', 'when', 'what', 'how', 'do', 'so', 'but', 'just', 'like',
    'all', 'or', 'an', 'if', 'get', 'no', 'we', 'your', 'was', 'am', 'im', 'cant', 'wont', 'dont',
    'has', 'had', 'been', 'there', 'they', 'their', 'them', 'any', 'some', 'more', 'new', 'now',
    'see', 'know', 'want', 'think', 'good', 'bad', 'fix', 'tried', 'trying', 'issue', 'problem',
    'still', 'again', 'after', 'before', 'premium', 'spotify', 'hear', 'sound', 'tracks', 'album',
    'artist', 'download', 'offline', 'logged', 'login', 'pass', 'password', 'card', 'payment',
    'charge', 'billed', 'subscription', 'student', 'family', 'cancel', 'reset', 'error', 'crashed',
    'yes', 'yeah', 'yep', 'nope', 'done', 'ok', 'okay', 'sure', 'hi', 'hello', 'hey', 'thanks', 'thank',
    'did', 'didnt', 'doesnt', 'isnt', 'arent', 'cannot', 'could', 'would', 'should', 'same', 'both',
    'mean', 'every', 'pauses', 'seconds', 'screen', 'nothing', 'everything', 'working', 'fixed', 'broken'
}

COMMON_ENGLISH_WORDS: Set[str] = {
    'connection', 'refused', 'failed', 'timeout', 'server', 'desktop', 'android', 'iphone',
    'ios', 'windows', 'mac', 'linux', 'wifi', 'cellular', 'cache', 'browser', 'web', 'player',
    'sync', 'synced', 'syncing', 'install', 'installed', 'reinstall', 'reinstalled', 'restarting',
    'restarted', 'screen', 'blank', 'black', 'pause', 'pausing', 'paused', 'volume', 'audio',
    'sound', 'speaker', 'bluetooth', 'headphones', 'stream', 'streaming', 'code', 'link',
    'version', 'support', 'setting', 'settings', 'email', 'address', 'user', 'username', 'receipt',
    'closed', 'connected', 'uninstalled', 'broken', 'working', 'stopped', 'restarted', 'crash',
    'ipad', 'ipod', 'pc', 'macbook', 'laptop', 'tablet', 'samsung', 'pixel', 'galaxy', 'device',
    'phone', 'chrome', 'safari', 'firefox', 'edge', 'update', 'updated', 'latest', 'offline'
}

VALID_SHORT_FOLLOWUPS: Set[str] = {
    'yes', 'no', 'yeah', 'yep', 'nope', 'done', 'ok', 'okay', 'sure',
    'thanks', 'thank', 'thx', 'hi', 'hello', 'hey', 'android', 'iphone',
    'ios', 'windows', 'mac', 'macbook', 'ipad', 'ipod', 'pc', 'desktop',
    'mobile', 'laptop', 'web', 'browser', 'chrome', 'safari', 'firefox',
    'spotify', 'premium', 'family', 'student', 'offline', 'online',
    'both', 'neither', 'none', 'all', 'everything', 'working', 'fixed',
    'broken', 'still', 'not', 'same', 'reinstalled', 'restarted', 'updated',
    'latest', 'tried', 'nothing', 'happening', 'crashed', 'blank', 'black',
    'samsung', 'pixel', 'galaxy', 'device', 'phone', 'tablet', 'app'
}

NON_ENGLISH_STOPWORDS: Set[str] = {
    # Spanish & Portuguese
    'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'que', 'en', 'por', 'para', 'con',
    'es', 'son', 'estoy', 'esta', 'está', 'mis', 'cuenta', 'cancion', 'canción', 'musica',
    'música', 'ayuda', 'como', 'cómo', 'mas', 'más', 'pero', 'porque', 'yo', 'tu', 'su',
    'nao', 'não', 'uma', 'umas', 'com', 'minha', 'meu', 'voce', 'você', 'ja', 'já', 'pra',
    'dele', 'dela', 'obrigado', 'obrigada', 'gracias', 'hola', 'olá', 'favor', 'porfavor', 'puedo', 'consigo',
    'tem', 'tenho', 'quero', 'ajuda', 'problema', 'musicas', 'músicas', 'tocando', 'si', 'sí',
    'funciona', 'funcionando', 'abrir', 'abre', 'cerrar', 'cierra', 'cuentas', 'pago', 'pagar',
    'cobro', 'tarjeta', 'buenas', 'buenos', 'dias', 'días', 'tardes', 'noches', 'reproducir',
    # French
    'le', 'les', 'du', 'des', 'une', 'et', 'dans', 'sur', 'pour', 'avec', 'je', 'ce', 'pas',
    'qui', 'mon', 'mes', 'est', 'suis', 'ne', 'merci', 'bonjour', 'compte', 'oui', 'non',
    'marche', 'fonctionne', 'musique', 'chanson',
    # German
    'und', 'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'nicht', 'mit', 'auf',
    'fur', 'für', 'ist', 'ich', 'sie', 'es', 'kann', 'mein', 'meine', 'bitte', 'hilfe',
    'ja', 'nein', 'danke', 'hallo', 'geht', 'funktioniert', 'lied', 'musik',
    # Italian
    'il', 'la', 'che', 'non', 'sono', 'per', 'una', 'della', 'dello', 'mio', 'mia', 'ciao',
    'grazie', 'prego', 'canzone', 'musica'
}


def clean_inquiry_text(text: str) -> str:
    """Strips URLs, user handles (including redacted @[CUSTOMER_HANDLE]), and excess whitespace."""
    if not text:
        return ""
    t = re.sub(r'https?://\S+', '', text)
    t = re.sub(r'@\[[^\]]+\]', '', t)
    t = re.sub(r'@[A-Za-z0-9_]+', '', t)
    return t.strip()


def detect_language_state(
    target_customer_text: str,
    ancestor_turns: Optional[List[Dict[str, Any]]] = None
) -> Tuple[str, float, str]:
    """
    Determines language state ('english', 'non_english', 'uncertain') and heuristic score.
    Uses target customer message and allowed prior ancestor turns (including prior brand questions).
    Excludes the selected future reply.
    
    Returns:
        (language_state, language_heuristic_score, detection_reason)
    """
    clean_target = clean_inquiry_text(target_customer_text)
    if len(clean_target) == 0:
        return LANGUAGE_STATE_UNCERTAIN, 0.0, "empty_text"
    if len(clean_target) < 2:
        return LANGUAGE_STATE_UNCERTAIN, 0.0, "too_short"

    # Non-Latin script check (Cyrillic, Arabic, CJK, Thai, Hebrew, etc.)
    non_latin = re.findall(
        r'[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF\u0E00-\u0E7F]',
        clean_target
    )
    if len(non_latin) >= 3:
        return LANGUAGE_STATE_NON_ENGLISH, 0.95, "non_latin_script"

    target_words = re.findall(r'[a-zA-Z\u00C0-\u024F]+', clean_target.lower())
    if not target_words:
        return LANGUAGE_STATE_UNCERTAIN, 0.0, "no_alphabetic_words"

    target_eng_count = sum(1 for w in target_words if w in ENGLISH_STOPWORDS)
    target_non_eng_count = sum(1 for w in target_words if w in NON_ENGLISH_STOPWORDS)
    target_common_count = sum(1 for w in target_words if w in COMMON_ENGLISH_WORDS)
    total_target_words = len(target_words)

    # 1. Target turn has explicit non-English stopwords
    # Critical rule: Do NOT let English ancestors override a clearly non-English target!
    if target_non_eng_count > 0 and target_non_eng_count >= target_eng_count:
        score = round(min(1.0, 0.5 + 0.15 * target_non_eng_count), 3)
        return LANGUAGE_STATE_NON_ENGLISH, score, "non_english_stopwords"

    # 2. Contextual short answers (e.g. "Yes", "Android", "Still broken", "Done", "iPhone")
    if total_target_words <= 3 and ancestor_turns:
        # Require target words to be recognized vocabulary, not Latin character gibberish
        recognized_target = all(
            w in ENGLISH_STOPWORDS or w in COMMON_ENGLISH_WORDS or w in VALID_SHORT_FOLLOWUPS or w.isdigit()
            for w in target_words
        )
        if recognized_target:
            prior_texts = [t.get("text", "") for t in ancestor_turns]
            prior_clean = clean_inquiry_text(" ".join(prior_texts))
            prior_words = re.findall(r'[a-zA-Z\u00C0-\u024F]+', prior_clean.lower())
            prior_eng = sum(1 for w in prior_words if w in ENGLISH_STOPWORDS)
            prior_non_eng = sum(1 for w in prior_words if w in NON_ENGLISH_STOPWORDS)
            if prior_eng >= 2 and prior_non_eng == 0:
                score = 0.85
                return LANGUAGE_STATE_ENGLISH, score, "contextual_english_short_answer"

    # Standalone queries that are too short or single-word have insufficient evidence
    if len(clean_target) < 4 or total_target_words < 2:
        return LANGUAGE_STATE_UNCERTAIN, 0.40, "too_short"

    # 3. Standard English stopwords match on target turn
    if target_eng_count >= 2:
        score = round(min(1.0, 0.60 + 0.08 * target_eng_count), 3)
        return LANGUAGE_STATE_ENGLISH, score, "english_stopwords_match"

    if target_eng_count == 1 and target_non_eng_count == 0:
        if total_target_words <= 5 or target_common_count >= 1:
            return LANGUAGE_STATE_ENGLISH, 0.75, "single_english_stopword"
        return LANGUAGE_STATE_UNCERTAIN, 0.45, "single_stopword_low_ratio"

    # 4. English technical terms without standard stopwords (e.g. "Connection refused")
    if target_common_count >= 1 and target_non_eng_count == 0:
        # Not confidently non-English! It is recognized technical English, reported as uncertain
        return LANGUAGE_STATE_UNCERTAIN, 0.50, "technical_terms_no_stopwords"

    # 5. Latin character gibberish (e.g. "asdfghjk qwertyuiop zxcvbnm")
    # Must NOT be classified as English merely because it uses ASCII/Latin characters
    return LANGUAGE_STATE_UNCERTAIN, 0.15, "unrecognized_tokens_insufficient_evidence"


def is_contextually_interpretable(
    target_customer_text: str,
    ancestor_turns: Optional[List[Dict[str, Any]]] = None,
    reply_text: str = ""
) -> Tuple[bool, str]:
    """
    Validates that a target customer turn is interpretable in context.
    Uses target text and allowed prior ancestor context turns (prior brand questions or customer turns).
    Excludes the held-out brand reply (reply_text is ignored for eligibility).
    """
    if not target_customer_text:
        return False, "empty_message"

    clean_cust = clean_inquiry_text(target_customer_text)
    if len(clean_cust) == 0:
        return False, "inquiry_too_short_or_empty"

    words = re.findall(r'\b\w+\b', clean_cust)

    # If target customer text alone has sufficient content
    if len(clean_cust) >= 4 and len(words) >= 2:
        return True, "valid"

    # If target is a short follow-up (e.g. "Yes", "Android", "Still broken", "Done", "No", "iPhone")
    # evaluate whether preceding ancestor turns explain it
    if ancestor_turns and len(ancestor_turns) > 0:
        prior_text = " ".join(t.get("text", "") for t in ancestor_turns)
        clean_prior = clean_inquiry_text(prior_text)
        prior_words = re.findall(r'\b\w+\b', clean_prior)
        if len(prior_words) >= 3:
            return True, "contextual_short_reply"

    if len(clean_cust) < 4:
        return False, "inquiry_too_short_or_empty"
    if len(words) < 2:
        return False, "insufficient_content_words"

    return True, "valid"


def export_human_review_sheet(
    sample_records: List[Dict[str, Any]],
    output_csv_path: Path
) -> None:
    """
    Creates a human verification review sheet with accepted, rejected, and uncertain examples.
    Human-label columns ('human_language_label', 'human_interpretability_label', 'human_notes')
    are left completely blank for authentic human annotation.
    """
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_category",
        "group_id",
        "target_customer_tweet_id",
        "prior_context_snippet",
        "target_customer_text",
        "language_state",
        "language_heuristic_score",
        "detection_reason",
        "human_language_label",
        "human_interpretability_label",
        "human_notes",
    ]

    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in sample_records:
            prior_snippet = ""
            if rec.get("ancestor_turns"):
                p_texts = []
                for t in rec["ancestor_turns"][:-1]:
                    is_inbound = bool(t.get("inbound", 0))
                    author_val = str(t.get("author_id", ""))
                    if not is_inbound or author_val.lower() == "spotifycares":
                        role = "Brand (SpotifyCares)"
                    else:
                        role = "Customer"
                    redacted_t = redact_sensitive_info(t.get("text", ""))
                    p_texts.append(f"[{role}]: {redacted_t}")
                full_prior = " | ".join(p_texts)
                prior_snippet = full_prior[:150]

            raw_target = rec.get("raw_customer_text") or rec.get("customer_text") or ""
            redacted_target = redact_sensitive_info(raw_target)

            writer.writerow({
                "sample_category": rec.get("sample_category", "evaluation"),
                "group_id": rec.get("group_id", ""),
                "target_customer_tweet_id": rec.get("target_customer_tweet_id", ""),
                "prior_context_snippet": prior_snippet,
                "target_customer_text": redacted_target,
                "language_state": rec.get("language_state", ""),
                "language_heuristic_score": rec.get("language_heuristic_score", ""),
                "detection_reason": rec.get("detection_reason", ""),
                "human_language_label": "",
                "human_interpretability_label": "",
                "human_notes": "",
            })
