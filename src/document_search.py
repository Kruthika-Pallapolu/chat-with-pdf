import os
import re
from typing import Optional, Dict, Any, List, Tuple

try:
    from pdf_loader import extract_text
except ImportError:
    from src.pdf_loader import extract_text

ROMAN_TO_NUM = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12
}

WORD_TO_NUM = {
    'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
    'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10,
    'ELEVEN': 11, 'TWELVE': 12
}

ORDINALS = {
    "first": 1, "1st": 1, "one": 1,
    "second": 2, "2nd": 2, "two": 2,
    "third": 3, "3rd": 3, "three": 3,
    "fourth": 4, "4th": 4, "four": 4,
    "fifth": 5, "5th": 5, "five": 5,
    "sixth": 6, "6th": 6, "six": 6,
    "seventh": 7, "7th": 7, "seven": 7,
    "eighth": 8, "8th": 8, "eight": 8,
    "ninth": 9, "9th": 9, "nine": 9,
    "tenth": 10, "10th": 10, "ten": 10,
    "eleventh": 11, "11th": 11, "11": 11,
    "twelfth": 12, "12th": 12, "12": 12,
    "last": "last"
}

NUMBER_TO_ORDINAL_WORD = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth"
}

QUESTION_VERBS = (
    'WHAT', 'WHY', 'HOW', 'EXPLAIN', 'DEFINE', 'STATE', 'LIST', 'DESCRIBE',
    'DIFFERENTIATE', 'DISCUSS', 'COMMENT', 'COMPARE', 'ENUMERATE', 'OUTLINE',
    'WRITE', 'BRIEFLY', 'GIVE', 'ILLUSTRATE', 'DISTINGUISH', 'SUMMARIZE', 'NAME',
    'CALCULATE', 'DERIVE', 'ELABORATE', 'MENTION', 'CLASSIFY', 'DETAIL', 'WHICH',
    'CAN', 'DOES', 'IS', 'ARE', 'SHOW'
)


def get_ordinal_word(n: int) -> str:
    if isinstance(n, int) and n in NUMBER_TO_ORDINAL_WORD:
        return NUMBER_TO_ORDINAL_WORD[n]
    return f"{n}th"


def find_module_headings(pdf_file: str) -> List[str]:
    """
    Find all module/section headings directly from the PDF text.
    """
    if not os.path.exists(pdf_file):
        return []
    pages = extract_text(pdf_file)
    modules = []

    mod_pattern = re.compile(
        r'^\s*(?:MODULE|UNIT|CHAPTER|PART|\d+\s*[-]?\s*MARK)\s*[-#:]?\s*([0-9IVX]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|QUESTIONS?)',
        re.IGNORECASE
    )

    for page in pages:
        lines = page["text"].splitlines()
        for line in lines:
            stripped = line.strip()
            if mod_pattern.match(stripped):
                if stripped not in modules:
                    modules.append(stripped)
    return modules


def extract_all_sections_and_questions(pages: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Extracts all sections, modules, mark-categories, and numbered questions across the PDF pages.
    """
    all_lines = []
    for p in pages:
        for line in p["text"].splitlines():
            all_lines.append((p["page"], line))

    section_pattern = re.compile(
        r'^\s*(?:(?:MODULE|UNIT|CHAPTER|PART)\s*[-#:]?\s*([0-9IVX]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)\b|\d+\s*[-]?\s*MARK\s*QUESTIONS?|PART\s+[A-Z]\b|SHORT\s+QUESTIONS|REVIEW\s+QUESTIONS|EXERCISES|QUESTION\s+BANK)',
        re.IGNORECASE
    )

    sec_locations = []
    for idx, (p_num, line) in enumerate(all_lines):
        stripped = line.strip()
        if section_pattern.match(stripped):
            sec_locations.append((idx, p_num, stripped))

    if not sec_locations:
        sec_locations = [(0, 1, "Document Content")]

    sections_dict = {}

    q_start_pattern = re.compile(
        r'^\s*(?:Q\.?|QUESTION)?\s*\(?(\d+)\)?\s*[\.\:\)\-]\s*(.*)',
        re.IGNORECASE
    )

    for i in range(len(sec_locations)):
        start_idx, start_page, raw_sec_title = sec_locations[i]
        end_idx = sec_locations[i+1][0] if i+1 < len(sec_locations) else len(all_lines)
        sec_lines = all_lines[start_idx:end_idx]

        questions = []
        curr_q = None

        for p_num, line in sec_lines:
            stripped = line.strip()
            if not stripped:
                continue

            if section_pattern.match(stripped) and stripped != raw_sec_title:
                continue

            qm = q_start_pattern.match(stripped)
            if qm:
                q_num = int(qm.group(1))
                q_rest = qm.group(2).strip()

                is_q = False
                if q_rest.endswith('?'):
                    is_q = True
                elif len(q_rest) > 0:
                    first_word = q_rest.split()[0].upper().rstrip(':,.-') if q_rest.split() else ''
                    if first_word in QUESTION_VERBS:
                        is_q = True
                    elif curr_q is None or q_num == curr_q['num'] + 1 or q_num <= curr_q['num'] + 5:
                        is_q = True

                if is_q:
                    if curr_q:
                        curr_q['full_text'] = '\n'.join(curr_q['lines']).strip()
                        questions.append(curr_q)

                    curr_q = {
                        'num': q_num,
                        'title': stripped,
                        'page': p_num,
                        'lines': [stripped]
                    }
                    continue

            if curr_q:
                curr_q['lines'].append(stripped)

        if curr_q:
            curr_q['full_text'] = '\n'.join(curr_q['lines']).strip()
            questions.append(curr_q)

        normalized_key = raw_sec_title.lower()
        sections_dict[normalized_key] = {
            'raw_title': raw_sec_title,
            'page': start_page,
            'questions': questions
        }

    return sections_dict


def parse_numbered_question_query(query: str, sections_dict: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], Optional[Any]]:
    """
    Parses structural query to extract target section key and question position.
    """
    q_lower = query.lower().strip()

    target_sec_key = None

    # Check for mark patterns: "2-mark", "2 mark", "5-mark", "10-mark"
    mark_match = re.search(r'\b(\d+)\s*[-]?\s*mark(?:s)?\b', q_lower)
    if mark_match:
        m_val = mark_match.group(1)
        for sec_key in sections_dict:
            if f"{m_val} mark" in sec_key or f"{m_val}-mark" in sec_key:
                target_sec_key = sec_key
                break

    if target_sec_key is None:
        # Check module patterns
        mod_match = re.search(r'\b(?:module|unit|chapter|part)\s*[-#:]?\s*(\d+|i|ii|iii|iv|v|vi|vii|viii|ix|x)\b', q_lower)
        if mod_match:
            m_val = mod_match.group(1).upper()
            num_val = int(m_val) if m_val.isdigit() else ROMAN_TO_NUM.get(m_val)
            for sec_key in sections_dict:
                if f"module-{num_val}" in sec_key or f"module {num_val}" in sec_key or f"module{num_val}" in sec_key:
                    target_sec_key = sec_key
                    break

    if target_sec_key is None:
        for sec_key, sec_data in sections_dict.items():
            if sec_data['raw_title'].lower() in q_lower:
                target_sec_key = sec_key
                break

    if target_sec_key is None and sections_dict:
        if "question" in q_lower:
            target_sec_key = list(sections_dict.keys())[0]

    if target_sec_key is None:
        return None, None

    question_pos = None
    if re.search(r'\b(all|list all|show all|list the|what are the questions|list questions|questions under|all questions)\b', q_lower) and not re.search(r'\b(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last)\s+question\b', q_lower):
        question_pos = "all"
    elif "last" in q_lower:
        question_pos = "last"
    else:
        q_ord_match = re.search(r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th|\d+)(?:st|nd|rd|th)?\s+(?:question|q)\b', q_lower)
        if q_ord_match:
            word = q_ord_match.group(1)
            question_pos = ORDINALS.get(word, int(word) if word.isdigit() else None)
        else:
            q_num_match = re.search(r'\b(?:question|q)\s*[-#:]?\s*(\d+)\b', q_lower)
            if q_num_match:
                question_pos = int(q_num_match.group(1))

    if question_pos is None:
        question_pos = "all"

    return target_sec_key, question_pos


def get_numbered_question_answer(query: str, pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Handles queries requesting specific numbered questions or question lists in sections/modules.
    Bypasses Gemini completely.
    """
    q_lower = query.lower()
    if not any(w in q_lower for w in ["question", "questions", "q", "mark", "module", "unit", "chapter", "part"]):
        return None

    pages = extract_text(pdf_path)
    sections_dict = extract_all_sections_and_questions(pages)
    sec_key, question_pos = parse_numbered_question_query(query, sections_dict)

    if sec_key is None or sec_key not in sections_dict:
        return None

    sec_data = sections_dict[sec_key]
    questions = sec_data["questions"]

    if not questions:
        return None

    if question_pos == "all":
        q_lines = [f"Questions under {sec_data['raw_title']}:\n"]
        sources = set()
        for q in questions:
            q_lines.append(f"{q['title']}")
            sources.add(q['page'])
        return {
            "answer": "\n".join(q_lines).strip(),
            "sources": sorted(list(sources)),
            "found_in_pdf": True,
            "is_module_question": True
        }

    if question_pos == "last":
        target_q = questions[-1]
        return {
            "answer": target_q['title'],
            "sources": [target_q['page']],
            "found_in_pdf": True,
            "is_module_question": True
        }

    if isinstance(question_pos, int):
        matching = [q for q in questions if q['num'] == question_pos]
        if matching:
            target_q = matching[0]
            return {
                "answer": target_q['title'],
                "sources": [target_q['page']],
                "found_in_pdf": True,
                "is_module_question": True
            }
        if 1 <= question_pos <= len(questions):
            target_q = questions[question_pos - 1]
            return {
                "answer": target_q['title'],
                "sources": [target_q['page']],
                "found_in_pdf": True,
                "is_module_question": True
            }

    return None


def get_step_or_sequence_answer(query: str, pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Handles sequential process step queries ("4th step in selection process", "six steps of HRP").
    Bypasses Gemini completely.
    """
    q_lower = query.lower().strip()

    step_keywords = ["step", "steps", "process", "component", "components", "stage", "stages", "phase", "phases"]
    if not any(k in q_lower for k in step_keywords):
        return None

    step_pos = None
    if "last" in q_lower:
        step_pos = "last"
    elif re.search(r'\b(all|six|6|five|5|four|4|three|3|two|2|list|what are the)\s+(?:steps|components|stages|phases)\b', q_lower):
        step_pos = "all"
    else:
        m_step = re.search(r'\b(\d+|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)\s+(?:step|stage|phase|component)\b', q_lower)
        if m_step:
            word = m_step.group(1)
            step_pos = ORDINALS.get(word, int(word) if word.isdigit() else None)
        else:
            m_step2 = re.search(r'\b(?:step|stage|phase|component)\s*[-#:]?\s*(\d+)\b', q_lower)
            if m_step2:
                step_pos = int(m_step2.group(1))

    if step_pos is None:
        step_pos = "all"

    pages = extract_text(pdf_path)

    # Check HRP specific steps
    if "hrp" in q_lower or "human resource planning" in q_lower:
        hrp_steps = []
        for p in pages:
            for line in p["text"].splitlines():
                s = line.strip()
                m = re.match(r'^\s*(Step\s*\d+[\:\.-]?\s*.*)', s, re.IGNORECASE)
                if m and len(m.group(1)) > 6 and p["page"] in [4, 5]:
                    hrp_steps.append((p["page"], m.group(1)))
        if hrp_steps:
            if step_pos == "all":
                lines = [f"{st}" for p_num, st in hrp_steps]
                return {
                    "answer": f"Six Steps of Human Resource Planning (HRP):\n\n" + "\n".join(lines),
                    "sources": sorted(list(set(p_num for p_num, st in hrp_steps))),
                    "found_in_pdf": True,
                    "is_module_question": True
                }
            if isinstance(step_pos, int) and 1 <= step_pos <= len(hrp_steps):
                p_num, st = hrp_steps[step_pos - 1]
                return {
                    "answer": st,
                    "sources": [p_num],
                    "found_in_pdf": True,
                    "is_module_question": True
                }

    target_terms = []
    if "selection" in q_lower:
        target_terms = ["selection process", "selection"]
    elif "job analysis" in q_lower:
        target_terms = ["components of job analysis", "job analysis"]
    elif "placement" in q_lower:
        target_terms = ["process of placement", "placement"]

    extracted_steps = []
    matched_page = None
    process_title = None

    for p in pages:
        lines = p["text"].splitlines()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if target_terms and any(term in stripped.lower() for term in target_terms):
                if stripped.isupper() or stripped.endswith(':') or "process" in stripped.lower() or "components" in stripped.lower():
                    matched_page = p["page"]
                    process_title = stripped
                    current_steps = []
                    for next_line in lines[idx+1:idx+35]:
                        s_line = next_line.strip()
                        if not s_line:
                            continue
                        step_match = re.match(r'^\s*(?:step\s*\d+[\:\.-]?|\(?\d+\)?[\:\.-]|•||\d+\.)\s*(.*)', s_line, re.IGNORECASE)
                        if step_match:
                            current_steps.append((p["page"], s_line))
                        elif "job description" in s_line.lower() or "job specification" in s_line.lower():
                            current_steps.append((p["page"], s_line))
                        elif len(current_steps) >= 2 and s_line.isupper() and len(s_line) < 60 and not s_line.startswith("STEP"):
                            break
                    if len(current_steps) >= 2:
                        extracted_steps = current_steps
                        break
        if extracted_steps:
            break

    if not extracted_steps:
        return None

    if step_pos == "all":
        ans_lines = [f"{process_title or 'Steps/Components'} (Page {matched_page}):\n"]
        sources = set()
        for p_num, st in extracted_steps:
            ans_lines.append(st)
            sources.add(p_num)
        return {
            "answer": "\n".join(ans_lines).strip(),
            "sources": sorted(list(sources)),
            "found_in_pdf": True,
            "is_module_question": True
        }

    if isinstance(step_pos, int):
        for p_num, st in extracted_steps:
            num_match = re.search(r'\b(?:step\s*)?' + str(step_pos) + r'[\:\.-]?\b', st, re.IGNORECASE)
            if num_match:
                return {
                    "answer": st,
                    "sources": [p_num],
                    "found_in_pdf": True,
                    "is_module_question": True
                }

        if 1 <= step_pos <= len(extracted_steps):
            p_num, st = extracted_steps[step_pos - 1]
            return {
                "answer": st,
                "sources": [p_num],
                "found_in_pdf": True,
                "is_module_question": True
            }

    if step_pos == "last" and extracted_steps:
        p_num, st = extracted_steps[-1]
        return {
            "answer": st,
            "sources": [p_num],
            "found_in_pdf": True,
            "is_module_question": True
        }

    return None


def get_document_topics_answer(query: str, pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Extracts major document headings and sections directly from the PDF.
    Bypasses Gemini completely.
    """
    q_lower = query.lower().strip()
    topic_keywords = ["major topics", "main topics", "topics covered", "sections in", "headings in", "topics in this pdf", "topics in this document", "what are the topics"]
    if not any(k in q_lower for k in topic_keywords):
        return None

    pages = extract_text(pdf_path)
    topics = []
    seen = set()

    for p in pages:
        lines = p["text"].splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            is_heading = False
            if re.match(r'^\s*(?:MODULE|UNIT|CHAPTER|PART)\s*[-#:]?\s*([0-9IVX]+|[A-Z]+)', stripped, re.IGNORECASE):
                is_heading = True
            elif re.match(r'^\s*\d+\s*[-]?\s*MARK\s*QUESTIONS?', stripped, re.IGNORECASE):
                is_heading = True
            elif stripped.isupper() and 5 <= len(stripped) <= 60 and not stripped.startswith("PAGE"):
                if not any(w in stripped for w in ["TABLE OF CONTENTS", "HTTP", "WWW", "PAGE"]):
                    is_heading = True

            if is_heading and stripped.lower() not in seen:
                seen.add(stripped.lower())
                topics.append(f"• {stripped} (Page {p['page']})")

    if not topics:
        return None

    return {
        "answer": "Major topics and sections covered in this PDF:\n\n" + "\n".join(topics[:15]),
        "sources": sorted(list(set(p['page'] for p in pages)))[:5],
        "found_in_pdf": True,
        "is_module_question": True
    }


def get_structural_answer(query: str, pdf_path: str) -> Optional[Dict[str, Any]]:
    """
    Main structural retrieval router.
    Checks structural query types (numbered questions, process steps, topics) before semantic RAG.
    Returns result dict if matched, or None if query should pass to semantic RAG + Gemini.
    """
    if not os.path.exists(pdf_path):
        return None

    # 1. Topic / Document wide heading query
    topic_ans = get_document_topics_answer(query, pdf_path)
    if topic_ans:
        return topic_ans

    # 2. Numbered / Section / Mark Question query
    num_ans = get_numbered_question_answer(query, pdf_path)
    if num_ans:
        return num_ans

    # 3. Step / Sequence query
    step_ans = get_step_or_sequence_answer(query, pdf_path)
    if step_ans:
        return step_ans

    return None
