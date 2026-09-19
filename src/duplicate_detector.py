"""
Duplicate Detection & Cluster Propagation Module

Implements:
1. Exact and near-duplicate customer inquiry detection with token Jaccard similarity.
2. Inverted index with prefix and length filtering over the full candidate population.
3. Preservation of semantic distinctions:
   - Negation polarity distinctions.
   - Error code distinctions.
   - Context-aware resolution for generic short replies incorporating prior customer context.
4. Transitive clustering (connected components) with stable deterministic cluster IDs.
5. Review and development exclusion propagation to all cluster members and canonical representatives.
"""

import re
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict, Counter

NEGATION_WORDS = {
    'not', 'no', 'never', 'cant', 'cannot', 'wont', 'dont',
    'isnt', 'didnt', 'neither', 'nor', 'without', 'unable'
}

GENERIC_SHORT_PHRASES = {
    'still broken', 'thank you', 'thanks', 'not working',
    'done', 'yes', 'no', 'okay', 'ok', 'it works', 'fixed',
    'tried that', 'did that', 'same problem', 'help please'
}


def normalize_inquiry(text: str) -> str:
    """
    Normalizes inquiry text:
    - Lowercase.
    - Strips URLs and user handles (including redacted handles @[CUSTOMER_HANDLE]).
    - Strips model input prefixes [Customer_1] (TARGET CUSTOMER INQUIRY):.
    - Removes punctuation, replaces with single space.
    - Collapses whitespace.
    """
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'\[customer_\d+\]\s*(?:\(target customer inquiry\))?:?', '', t)
    t = re.sub(r'@\[[^\]]+\]', '', t)
    t = re.sub(r'@[a-z0-9_]+', '', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t



def extract_error_codes(text: str) -> Set[str]:
    """
    Extracts distinct error codes or numeric/hex identifiers from customer message text.
    Preserves distinctions like 'error 404' vs 'error 500' or '0x80070005'.
    """
    if not text:
        return set()
    codes = set()
    matches = re.findall(r'\b(?:error|code|err)\s*#?([0-9a-zA-Z_-]+)\b', text.lower())
    for m in matches:
        if any(c.isdigit() for c in m):
            codes.add(m)
    hex_matches = re.findall(r'\b0x[0-9a-fA-F]+\b', text.lower())
    for h in hex_matches:
        codes.add(h)
    return codes


def extract_negations(text: str) -> Set[str]:
    """Extracts negation tokens present in normalized inquiry."""
    words = set(text.lower().split())
    return words & NEGATION_WORDS


def get_effective_inquiry(candidate: Dict[str, Any]) -> str:
    """
    Returns the effective inquiry string used for duplicate comparison.
    If the target customer message is a generic short reply (e.g. 'Still broken', 'Thank you')
    and has prior customer turns in allowed ancestor context, incorporates the prior customer turns
    so that unrelated threads are not falsely merged solely on the follow-up phrase.
    """
    norm_inquiry = candidate.get("normalized_inquiry")
    if norm_inquiry is None:
        target_text = candidate.get("customer_text") or candidate.get("raw_customer_text") or ""
        norm_inquiry = normalize_inquiry(target_text)

    words = norm_inquiry.split()
    is_short = len(words) <= 3
    is_generic = norm_inquiry in GENERIC_SHORT_PHRASES

    ancestor_turns = candidate.get("ancestor_turns") or []
    if (is_short or is_generic) and len(ancestor_turns) > 1:
        # Collect prior customer turns in ancestor context (excluding brand replies)
        prior_cust_turns = [
            t.get("text", "") for t in ancestor_turns[:-1]
            if t.get("inbound") == 1 or (t.get("author_id") and t.get("author_id") != "SpotifyCares")
        ]
        if prior_cust_turns:
            combined_prior = " ".join(prior_cust_turns)
            prior_norm = normalize_inquiry(combined_prior)
            if prior_norm:
                return f"{prior_norm} {norm_inquiry}".strip()

    return norm_inquiry


def compute_token_jaccard(text1: str, text2: str) -> float:
    """Computes Jaccard similarity between word tokens of two texts."""
    tokens1 = set(text1.split())
    tokens2 = set(text2.split())
    if not tokens1 or not tokens2:
        return 0.0
    return len(tokens1 & tokens2) / len(tokens1 | tokens2)


def find_duplicate_pairs_inverted_index(
    candidates: List[Dict[str, Any]],
    similarity_threshold: float = 0.85
) -> List[Tuple[str, str, float, str]]:
    """
    Finds exact and near-duplicate pairs across the full candidate list using an inverted
    index with prefix and length filtering.
    
    Returns a list of tuples: (group_id_1, group_id_2, similarity, match_type)
    where match_type is 'exact' or 'near'.
    """
    # 1. Preprocess each candidate
    prepared: List[Dict[str, Any]] = []
    for c in candidates:
        gid = str(c["group_id"])
        eff_text = get_effective_inquiry(c)
        raw_text = c.get("raw_customer_text") or c.get("customer_text") or ""
        tokens = set(eff_text.split())
        prepared.append({
            "group_id": gid,
            "effective_text": eff_text,
            "raw_text": raw_text,
            "tokens": tokens,
            "token_count": len(tokens),
            "negations": tokens & NEGATION_WORDS,
            "error_codes": extract_error_codes(raw_text),
            "orig_index": len(prepared),
        })

    # 2. Fast exact duplicate grouping by effective text
    exact_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in prepared:
        exact_groups[item["effective_text"]].append(item)

    pairs: List[Tuple[str, str, float, str]] = []
    seen_pair_keys: Set[Tuple[str, str]] = set()

    def add_pair(gid1: str, gid2: str, sim: float, m_type: str):
        k = (gid1, gid2) if gid1 < gid2 else (gid2, gid1)
        if k not in seen_pair_keys and gid1 != gid2:
            seen_pair_keys.add(k)
            pairs.append((k[0], k[1], round(sim, 4), m_type))

    for eff_text, items in exact_groups.items():
        if len(items) > 1 and eff_text.strip():
            # All items with identical effective text match exactly
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    # Ensure negation and error code consistency even for exact matches
                    if items[i]["negations"] != items[j]["negations"]:
                        continue
                    if items[i]["error_codes"] and items[j]["error_codes"] and (items[i]["error_codes"] != items[j]["error_codes"]):
                        continue
                    add_pair(items[i]["group_id"], items[j]["group_id"], 1.0, "exact")

    # 3. Near-duplicate search with inverted index, prefix and length filtering
    valid_items = [item for item in prepared if item["token_count"] > 0]

    # Calculate token frequencies across the universe
    token_freq: Counter = Counter()
    for item in valid_items:
        token_freq.update(item["tokens"])

    # Order each candidate's tokens by frequency (rarest first)
    for item in valid_items:
        item["sorted_tokens"] = sorted(list(item["tokens"]), key=lambda t: (token_freq[t], t))

    # Sort candidates by token count for length filtering
    valid_items.sort(key=lambda x: x["token_count"])

    inverted_index: Dict[str, List[int]] = defaultdict(list)

    for i, item_i in enumerate(valid_items):
        gid_i = item_i["group_id"]
        tokens_i = item_i["tokens"]
        len_i = item_i["token_count"]
        sorted_tokens_i = item_i["sorted_tokens"]

        # Prefix length for item_i
        p_len_i = len_i - int(len_i * similarity_threshold) + 1
        prefix_i = sorted_tokens_i[:p_len_i]

        candidates_seen: Set[int] = set()
        for tok in prefix_i:
            for j in inverted_index[tok]:
                if j in candidates_seen:
                    continue
                candidates_seen.add(j)
                item_j = valid_items[j]
                gid_j = item_j["group_id"]

                if gid_i == gid_j:
                    continue

                len_j = item_j["token_count"]
                # Length filter: len_j <= len_i since j was indexed earlier
                if len_j < len_i * similarity_threshold:
                    continue

                # Preserve negation distinction
                if item_i["negations"] != item_j["negations"]:
                    continue

                # Preserve error code distinction
                if item_i["error_codes"] and item_j["error_codes"] and (item_i["error_codes"] != item_j["error_codes"]):
                    continue

                # Compute Jaccard
                intersect = len(tokens_i & item_j["tokens"])
                union = len(tokens_i | item_j["tokens"])
                sim = intersect / union if union > 0 else 0.0

                if sim >= similarity_threshold:
                    m_type = "exact" if sim == 1.0 else "near"
                    add_pair(gid_j, gid_i, sim, m_type)

        # Add item_i to inverted index under its prefix tokens
        for tok in prefix_i:
            inverted_index[tok].append(i)

    return pairs


def build_transitive_clusters(
    candidates: List[Dict[str, Any]],
    duplicate_pairs: List[Tuple[str, str, float, str]]
) -> List[Dict[str, Any]]:
    """
    Builds deterministic transitive duplicate clusters (connected components).
    Handles transitive connections: A matches B and B matches C => {A, B, C}.
    Assigns stable cluster IDs and selects a deterministic canonical representative.
    """
    # Build adjacency graph
    all_gids: Set[str] = {str(c["group_id"]) for c in candidates}
    adj: Dict[str, Set[str]] = defaultdict(set)
    pair_sims: Dict[Tuple[str, str], float] = {}

    for gid1, gid2, sim, m_type in duplicate_pairs:
        if gid1 in all_gids and gid2 in all_gids:
            adj[gid1].add(gid2)
            adj[gid2].add(gid1)
            pair_sims[(min(gid1, gid2), max(gid1, gid2))] = sim

    visited: Set[str] = set()
    clusters: List[Dict[str, Any]] = []

    # Sort all group IDs deterministically
    def sort_key(gid: str):
        return (int(gid) if gid.isdigit() else float('inf'), gid)

    sorted_all_gids = sorted(list(all_gids), key=sort_key)

    for gid in sorted_all_gids:
        if gid in visited:
            continue

        # BFS / connected component
        component: List[str] = []
        queue = [gid]
        visited.add(gid)

        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for neighbor in sorted(list(adj[curr]), key=sort_key):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Deterministic sorting of cluster members
        component.sort(key=sort_key)
        canonical_gid = component[0]
        cluster_id = f"cluster_{canonical_gid}"

        # Collect internal pair similarities for audit
        internal_edges = []
        for i in range(len(component)):
            for j in range(i + 1, len(component)):
                k = (min(component[i], component[j]), max(component[i], component[j]))
                if k in pair_sims:
                    internal_edges.append({
                        "group_1": k[0],
                        "group_2": k[1],
                        "similarity": pair_sims[k]
                    })

        clusters.append({
            "cluster_id": cluster_id,
            "canonical_group_id": canonical_gid,
            "member_group_ids": component,
            "size": len(component),
            "internal_edges": internal_edges,
            "has_duplicates": len(component) > 1,
        })

    # Sort clusters deterministically by canonical_group_id
    clusters.sort(key=lambda c: sort_key(c["canonical_group_id"]))
    return clusters


def load_exclusion_history(
    brand_review_dir: Path,
    dev_inputs_path: Optional[Path] = None,
    brand_name: str = "SpotifyCares"
) -> Dict[str, Any]:
    """
    Collects reviewed root IDs from all available manifests and review sheets,
    along with development group IDs.
    Calculates SHA256 checksums for each loaded source without hardcoded counts.
    """
    sources_loaded: List[Dict[str, Any]] = []
    reviewed_root_ids: Set[str] = set()

    manifest_candidates = [
        ("original_sampling_manifest.json", brand_review_dir / "original_sampling_manifest.json"),
        ("sampling_manifest_original_uploaded.json", brand_review_dir / "sampling_manifest_original_uploaded.json"),
        ("sampling_manifest_v1.json", brand_review_dir / "sampling_manifest_v1.json"),
        ("sampling_manifest.json", brand_review_dir / "sampling_manifest.json"),
    ]

    for name, path in manifest_candidates:
        if path.exists():
            content_bytes = path.read_bytes()
            sha = hashlib.sha256(content_bytes).hexdigest()
            file_roots: Set[str] = set()
            try:
                data = json.loads(content_bytes.decode('utf-8'))
                for c in data.get("conversations", []):
                    if c.get("brand") == brand_name and "root_tweet_id" in c:
                        file_roots.add(str(c["root_tweet_id"]))
            except Exception as e:
                pass
            reviewed_root_ids.update(file_roots)
            sources_loaded.append({
                "source_name": name,
                "file_path": str(path),
                "sha256": sha,
                "unique_roots_contributed": len(file_roots),
                "roots_sample": sorted(list(file_roots))[:5]
            })

    review_csv_path = brand_review_dir / "review_scores.csv"
    if review_csv_path.exists():
        content_bytes = review_csv_path.read_bytes()
        sha = hashlib.sha256(content_bytes).hexdigest()
        csv_roots: Set[str] = set()
        try:
            import pandas as pd
            df = pd.read_csv(review_csv_path, dtype=str, keep_default_na=False)
            if "root_tweet_id" in df.columns:
                for r in df["root_tweet_id"].dropna():
                    r_clean = str(r).strip()
                    if r_clean:
                        csv_roots.add(r_clean)
        except Exception:
            pass
        reviewed_root_ids.update(csv_roots)
        sources_loaded.append({
            "source_name": "review_scores.csv",
            "file_path": str(review_csv_path),
            "sha256": sha,
            "unique_roots_contributed": len(csv_roots),
            "roots_sample": sorted(list(csv_roots))[:5]
        })

    # Development group IDs
    dev_group_ids: Set[str] = set()
    if dev_inputs_path and dev_inputs_path.exists():
        content_bytes = dev_inputs_path.read_bytes()
        sha = hashlib.sha256(content_bytes).hexdigest()
        try:
            with open(dev_inputs_path, "r", encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    if "group_id" in rec:
                        dev_group_ids.add(str(rec["group_id"]))
        except Exception:
            pass
        sources_loaded.append({
            "source_name": "dev_inputs.jsonl",
            "file_path": str(dev_inputs_path),
            "sha256": sha,
            "unique_roots_contributed": len(dev_group_ids),
            "roots_sample": sorted(list(dev_group_ids))[:5]
        })

    all_restricted_roots = reviewed_root_ids | dev_group_ids

    return {
        "sources_loaded": sources_loaded,
        "reviewed_root_ids_count": len(reviewed_root_ids),
        "reviewed_root_ids": sorted(list(reviewed_root_ids)),
        "dev_group_ids_count": len(dev_group_ids),
        "dev_group_ids": sorted(list(dev_group_ids)),
        "total_restricted_roots_count": len(all_restricted_roots),
        "all_restricted_roots": sorted(list(all_restricted_roots)),
    }


def propagate_restrictions_to_clusters(
    clusters: List[Dict[str, Any]],
    restricted_root_ids: Set[str]
) -> List[Dict[str, Any]]:
    """
    Propagates review/development evaluation restrictions across clusters.
    If ANY member of a cluster is in restricted_root_ids, the ENTIRE cluster
    and its canonical representative are marked ineligible for evaluation.
    """
    updated_clusters = []
    for c in clusters:
        members_set = set(c["member_group_ids"])
        overlapping_restrictions = members_set & restricted_root_ids
        is_restricted = len(overlapping_restrictions) > 0

        updated_cluster = {
            **c,
            "ineligible_for_eval": is_restricted,
            "restricted_members": sorted(list(overlapping_restrictions)),
            "restricted_due_to": "review_or_dev_exposure" if is_restricted else "none"
        }
        updated_clusters.append(updated_cluster)

    return updated_clusters
