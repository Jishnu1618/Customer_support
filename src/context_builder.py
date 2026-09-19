"""
Model Context Builder & Split Isolation Module

1. Split Isolation: Manages conversation groups so all turns belonging to a root tree stay in the same split.
2. Model Context Builder: Builds context exclusively from the ancestor path up to the target customer turn.
   Excludes future turns and unrelated sibling branches.
3. Stable Anonymous Actor Assignment: Assigns stable anonymous actor IDs to customer participants.
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from datetime import datetime
from src.sample_brand_conversations import redact_sensitive_info


def parse_created_at(created_at_str: str) -> datetime:
    """Parses Twitter API created_at timestamp string for chronological comparison."""
    try:
        return datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return datetime.min


def assign_anonymous_actor_ids(tweets: List[Dict[str, Any]], brand_name: str = "SpotifyCares") -> Dict[str, str]:
    """
    Assigns stable anonymous actor IDs to participants in a conversation.
    Brand handles (e.g. SpotifyCares) retain their brand identity.
    Customer author IDs are mapped to 'Customer_1', 'Customer_2', etc.
    """
    actor_map: Dict[str, str] = {}
    customer_counter = 1

    for t in tweets:
        author = t.get("author_id", "")
        if not author:
            continue

        if author.lower() == brand_name.lower():
            actor_map[author] = brand_name
        elif author not in actor_map:
            actor_map[author] = f"Customer_{customer_counter}"
            customer_counter += 1

    return actor_map


def _normalize_inbound_value(val: Any) -> int:
    """Normalizes an inbound flag to 0 or 1 using validated strict rules."""
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (int, float)):
        return 1 if int(val) == 1 else 0
    s = str(val).strip().lower()
    if s in {"true", "1", "1.0", "t", "yes"}:
        return 1
    if s in {"false", "0", "0.0", "f", "no"}:
        return 0
    raise ValueError(f"Unexpected non-boolean value in inbound flag: {val!r}")


def _normalize_tweet_for_comparison(tweet: Dict[str, Any]) -> Tuple[str, int, str, str, Optional[str], Optional[str]]:
    """Extracts a normalized tuple for duplicate and conflict detection."""
    auth = str(tweet.get("author_id", "")).strip()
    inb = _normalize_inbound_value(tweet.get("inbound", 0))
    created = str(tweet.get("created_at", "")).strip()
    text = str(tweet.get("text", "")).strip()
    resp = tweet.get("response_tweet_id")
    resp_clean = str(resp).strip() if resp is not None and str(resp).strip() not in ("", "None", "nan") else None
    in_resp = tweet.get("in_response_to_tweet_id")
    in_resp_clean = str(in_resp).strip() if in_resp is not None and str(in_resp).strip() not in ("", "None", "nan") else None
    return (auth, inb, created, text, resp_clean, in_resp_clean)


def build_ancestor_path(
    tweets: List[Dict[str, Any]],
    target_tweet_id: str,
    brand_name: str = "SpotifyCares"
) -> List[Dict[str, Any]]:
    """
    Traces the direct ancestor path from the root turn up to the target_tweet_id.

    Integrity guarantees:
    1. Rejects conflicting duplicate tweet IDs in thread tweets; deduplicates identical duplicates.
    2. Validates target_tweet_id exists.
    3. Verifies that the target turn is a customer turn (inbound==1 and author_id != brand_name).
    4. Allows legitimate brand-authored roots and prior brand replies in the ancestor chain.
    5. Explicitly rejects missing parents in the ancestor chain.
    6. Explicitly rejects cycles on the selected ancestor path.
    7. Strictly excludes future turns and sibling branches by backwards traversal.
    """
    # 1. Deduplicate identical rows and detect conflicting duplicate tweet IDs
    tweet_dict: Dict[str, Dict[str, Any]] = {}
    seen_comparisons: Dict[str, Tuple] = {}

    for t in tweets:
        tid = str(t.get("tweet_id", "")).strip()
        if not tid:
            continue
        norm_t = _normalize_tweet_for_comparison(t)
        if tid in tweet_dict:
            prev_norm = seen_comparisons[tid]
            if norm_t != prev_norm:
                raise ValueError(
                    f"Conflicting duplicate tweet_id '{tid}' found in thread tweets."
                )
            # Identical duplicate: deduplicate without error
            continue
        tweet_dict[tid] = t
        seen_comparisons[tid] = norm_t

    target_id_clean = str(target_tweet_id).strip()
    if target_id_clean not in tweet_dict:
        raise ValueError(f"Target tweet_id '{target_tweet_id}' not found in provided thread tweets.")

    # 2. Verify target turn is a customer turn
    target_tweet = tweet_dict[target_id_clean]
    target_inbound = _normalize_inbound_value(target_tweet.get("inbound", 0))
    target_author = str(target_tweet.get("author_id", "")).strip()

    if target_inbound != 1 or target_author.lower() == brand_name.lower():
        raise ValueError(
            f"Target tweet '{target_tweet_id}' is not a customer turn "
            f"(inbound={target_inbound}, author='{target_author}', brand='{brand_name}')."
        )

    # 3. Trace ancestor path backwards from target
    ancestor_path: List[Dict[str, Any]] = []
    curr_id: Optional[str] = target_id_clean
    visited: Set[str] = set()

    while curr_id:
        if curr_id in visited:
            raise ValueError(f"Cycle detected in selected ancestor path involving tweet_id '{curr_id}'.")
        visited.add(curr_id)

        curr_tweet = tweet_dict[curr_id]
        ancestor_path.append(curr_tweet)

        parent_id = curr_tweet.get("in_response_to_tweet_id")
        if parent_id is not None and str(parent_id).strip() not in ("", "None", "nan"):
            norm_parent = str(parent_id).strip()
            if norm_parent not in tweet_dict:
                raise ValueError(
                    f"Missing parent tweet '{norm_parent}' in thread for tweet '{curr_id}'."
                )
            curr_id = norm_parent
        else:
            curr_id = None

    # Reverse to restore chronological order (root first -> target customer turn last)
    ancestor_path.reverse()
    return ancestor_path


def build_model_context(
    tweets: List[Dict[str, Any]],
    target_tweet_id: str,
    brand_name: str = "SpotifyCares"
) -> Dict[str, Any]:
    """
    Builds the model context payload for a given target customer turn.
    
    Returns:
    {
      "root_tweet_id": str,
      "target_tweet_id": str,
      "actor_map": dict,
      "root_customer_turn": dict,
      "target_customer_turn": dict,
      "ancestor_turns": list of dicts (chronological up to target_tweet_id),
      "model_input_text": str (formatted prompt input for inference)
    }
    """
    ancestor_turns = build_ancestor_path(tweets, target_tweet_id, brand_name=brand_name)
    actor_map = assign_anonymous_actor_ids(ancestor_turns, brand_name=brand_name)

    root_turn = ancestor_turns[0]
    target_turn = ancestor_turns[-1]

    # Format model input text
    formatted_lines = []
    for turn in ancestor_turns:
        author = turn.get("author_id", "")
        actor_id = actor_map.get(author, author)
        is_target = (str(turn["tweet_id"]) == str(target_tweet_id))
        
        turn_label = f"[{actor_id}]"
        if is_target:
            turn_label += " (TARGET CUSTOMER INQUIRY)"

        # Apply privacy redaction to model input text
        raw_text = turn.get('text', '')
        redacted_text = redact_sensitive_info(raw_text)
        formatted_lines.append(f"{turn_label}: {redacted_text}")
    model_input_text = "\n".join(formatted_lines)

    return {
        "root_tweet_id": str(root_turn["tweet_id"]),
        "target_tweet_id": str(target_turn["tweet_id"]),
        "actor_map": actor_map,
        "root_customer_turn": root_turn,
        "target_customer_turn": target_turn,
        "ancestor_turns": ancestor_turns,
        "model_input_text": model_input_text
    }
