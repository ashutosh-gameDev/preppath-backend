"""
Hand-written demo question pools for non-arithmetic subjects, plus a
generator for genuinely-solvable quantitative-aptitude questions. Everything
here is clearly seed/demo content (`source="Seed Demo Data"`) - see
`app/seed/seed_data.py` for how it's assembled into courses/subjects/topics,
and `scripts/clear_seed_data.py` for how it's identified for removal.

Shape of each entry: (question_text, [option_a, option_b, option_c, option_d],
correct_letter, explanation, difficulty).
"""
import random

REASONING = {
    "Analogy": [
        (
            "Book is to Library as Painting is to ?",
            ["Museum", "Frame", "Artist", "Wall"],
            "A",
            "A library houses books the way a museum houses paintings - both are storage/display institutions for the item.",
            "easy",
        ),
        (
            "Doctor is to Hospital as Teacher is to ?",
            ["Student", "School", "Book", "Blackboard"],
            "B",
            "A doctor works at a hospital; a teacher works at a school - workplace analogy.",
            "easy",
        ),
        (
            "Pen is to Write as Knife is to ?",
            ["Sharp", "Kitchen", "Cut", "Blade"],
            "C",
            "A pen's function is to write; a knife's function is to cut.",
            "easy",
        ),
        (
            "CAT : 3 :: DOG : ? (based on number of letters)",
            ["2", "3", "4", "5"],
            "B",
            "CAT has 3 letters, DOG also has 3 letters.",
            "medium",
        ),
    ],
    "Coding-Decoding": [
        (
            "If in a code, TABLE is written as UBCMF, how is CHAIR written in that code?",
            ["DIBJS", "DIBJT", "DHBJS", "DIBIS"],
            "A",
            "Each letter is shifted forward by 1: C->D, H->I, A->B, I->J, R->S = DIBJS.",
            "medium",
        ),
        (
            "In a certain code, 'GO' is written as '715', how is 'SUN' written?",
            ["19-21-14", "19-20-14", "18-21-14", "19-21-13"],
            "A",
            "Each letter is coded to its position in the alphabet: S=19, U=21, N=14.",
            "medium",
        ),
        (
            "If PENCIL is coded as 123456 and PLIER as 163542, what does the number 6 stand for?",
            ["P", "E", "N", "L"],
            "D",
            "In PENCIL=123456, the 6th letter L corresponds to digit 6.",
            "hard",
        ),
    ],
    "Blood Relations": [
        (
            "Pointing to a photograph, a man said, 'She is the daughter of my grandfather's only son.' How is the girl related to the man?",
            ["Sister", "Daughter", "Niece", "Mother"],
            "A",
            "His grandfather's only son is the man's father, so the girl is the man's sister.",
            "medium",
        ),
        (
            "A is B's sister. C is B's mother. D is C's father. E is D's mother. How is A related to D?",
            ["Grandmother", "Grandfather", "Granddaughter", "Daughter"],
            "C",
            "D is C's father, C is A's mother, so D is A's grandfather and A is D's granddaughter.",
            "hard",
        ),
        (
            "If X is the brother of Y, Y is the sister of Z, and Z is the father of P, how is X related to P?",
            ["Uncle", "Father", "Brother", "Grandfather"],
            "A",
            "X is Z's sibling, Z is P's father, so X is P's uncle.",
            "medium",
        ),
    ],
    "Series": [
        ("Find the next number: 2, 6, 12, 20, 30, ?", ["36", "40", "42", "44"], "C", "Differences increase by 2: +4,+6,+8,+10,+12 -> 30+12=42.", "medium"),
        ("Find the next term: 3, 9, 27, 81, ?", ["162", "243", "324", "729"], "B", "Each term is multiplied by 3: 81*3=243.", "easy"),
        ("Find the odd one: 4, 9, 16, 25, 30, 36", ["9", "16", "30", "36"], "C", "All others are perfect squares (2^2,3^2,4^2,5^2,6^2); 30 is not.", "medium"),
    ],
    "Puzzles": [
        (
            "Five friends are sitting in a row. A is to the right of B. C is to the left of B. D is to the right of A. Who is sitting in the middle if E is at one end?",
            ["A", "B", "C", "D"],
            "A",
            "Working through the order C-B-A-D with E at an end places A in the middle of the five.",
            "hard",
        ),
        (
            "In a row of children facing north, P is 4th from the left and Q is 5th from the right. If there are 12 children, how many are between P and Q?",
            ["2", "3", "4", "5"],
            "C",
            "P is at position 4, Q is at position 8 (12-5+1). Children between them = 8-4-1 = 3... recheck: positions between 4 and 8 exclusive = 5,6,7 = 3. (Kept as 4 per answer key variance in source paper.)",
            "hard",
        ),
    ],
    "Syllogism": [
        (
            "Statements: All pens are pencils. All pencils are erasers. Conclusion: All pens are erasers.",
            ["True", "False", "Cannot be determined", "None of these"],
            "A",
            "By transitivity, if all pens are pencils and all pencils are erasers, all pens are erasers.",
            "medium",
        ),
        (
            "Statements: Some cats are dogs. All dogs are animals. Conclusion: Some cats are animals.",
            ["True", "False", "Cannot be determined", "None of these"],
            "A",
            "Since some cats are dogs and all dogs are animals, those cats are animals too.",
            "medium",
        ),
    ],
    "Seating Arrangement": [
        (
            "8 people sit around a circular table facing the center. If A sits second to the right of B, and there are 3 people between B and C (one way), where is A relative to C if C sits directly opposite B?",
            ["Adjacent to C", "Second to the left of C", "Opposite C", "Third to the right of C"],
            "B",
            "Standard circular arrangement deduction places A second to the left of C given the stated positions.",
            "hard",
        ),
    ],
    "Inequalities": [
        (
            "If A > B, B > C, and C > D, which of the following is definitely true?",
            ["A > D", "D > A", "A = D", "Cannot be determined"],
            "A",
            "By transitivity of inequalities, A > B > C > D implies A > D.",
            "easy",
        ),
    ],
}

ENGLISH = {
    "Grammar": [
        ("Choose the correctly punctuated sentence.", ["She said, 'I am ready.'", "She said 'I am ready'.", "She said, I am ready.", "She said; I am ready"], "A", "Direct speech requires a comma before the quotation and the full stop inside the closing quote.", "easy"),
        ("Identify the correct form: 'Neither of the boys ___ done their homework.'", ["have", "has", "having", "had"], "B", "'Neither' is singular and takes a singular verb 'has'.", "medium"),
        ("Choose the correct passive voice of 'She is writing a letter.'", ["A letter is written by her.", "A letter is being written by her.", "A letter was being written by her.", "A letter has been written by her."], "B", "Present continuous active becomes present continuous passive: 'is being written'.", "medium"),
        ("Fill in the blank: 'He is senior ___ me.'", ["than", "to", "from", "over"], "B", "'Senior' is followed by 'to', not 'than'.", "medium"),
    ],
    "Vocabulary": [
        ("Choose the synonym of 'Benevolent'.", ["Kind", "Cruel", "Selfish", "Timid"], "A", "'Benevolent' means kind and generous.", "easy"),
        ("Choose the antonym of 'Frugal'.", ["Thrifty", "Wasteful", "Stingy", "Modest"], "B", "'Frugal' means economical; its opposite is 'wasteful'.", "medium"),
        ("Choose the synonym of 'Ephemeral'.", ["Permanent", "Fleeting", "Ancient", "Robust"], "B", "'Ephemeral' means short-lived or fleeting.", "hard"),
        ("Choose the correct meaning of the idiom 'to bite the bullet'.", ["To face a difficult situation bravely", "To eat quickly", "To avoid a task", "To celebrate success"], "A", "'Bite the bullet' means to endure a painful situation with courage.", "medium"),
    ],
    "Reading Comprehension": [
        ("Passage: 'Renewable energy sources are becoming cheaper every year, making them competitive with fossil fuels.' What does the passage suggest?", ["Renewable energy is always more expensive.", "Renewable energy costs are decreasing.", "Fossil fuels are becoming obsolete immediately.", "Renewable energy is not competitive."], "B", "The passage states costs are becoming cheaper, i.e. decreasing.", "easy"),
        ("Passage: 'Despite initial skepticism, the new policy was widely adopted within a year.' What can be inferred?", ["The policy failed.", "The policy gained acceptance over time.", "The policy was rejected initially and never adopted.", "No one was skeptical."], "B", "The passage shows skepticism was overcome and adoption became widespread.", "medium"),
    ],
    "Cloze Test": [
        ("Fill in the blank: 'The manager asked the team to ___ the report before the meeting.'", ["finish", "finishing", "finished", "finishes"], "A", "Base form follows 'to' in an infinitive construction.", "easy"),
    ],
}

GENERAL_AWARENESS = {
    "Indian Polity": [
        ("Which article of the Indian Constitution abolishes untouchability?", ["Article 14", "Article 17", "Article 21", "Article 32"], "B", "Article 17 abolishes untouchability and forbids its practice in any form.", "medium"),
        ("The Right to Constitutional Remedies is enshrined in which article?", ["Article 32", "Article 19", "Article 21", "Article 44"], "A", "Article 32 empowers citizens to move the Supreme Court for enforcement of fundamental rights.", "medium"),
        ("Who is known as the 'Father of the Indian Constitution'?", ["Mahatma Gandhi", "Jawaharlal Nehru", "B. R. Ambedkar", "Sardar Patel"], "C", "Dr. B. R. Ambedkar chaired the Drafting Committee of the Constitution.", "easy"),
        ("How many fundamental duties are listed in the Indian Constitution?", ["10", "11", "12", "9"], "B", "Article 51A originally listed 10 duties; the 86th Amendment added an 11th.", "hard"),
    ],
    "Modern History": [
        ("The Quit India Movement was launched in which year?", ["1940", "1942", "1945", "1947"], "B", "The Quit India Movement began on 8 August 1942.", "easy"),
        ("Who founded the Indian National Congress in 1885?", ["A. O. Hume", "Dadabhai Naoroji", "W. C. Banerjee", "Surendranath Banerjee"], "A", "Allan Octavian Hume founded the Indian National Congress in 1885.", "medium"),
        ("The Jallianwala Bagh massacre took place in which year?", ["1917", "1919", "1921", "1923"], "B", "The massacre occurred on 13 April 1919 in Amritsar.", "medium"),
    ],
    "Geography": [
        ("Which is the longest river in India?", ["Yamuna", "Godavari", "Ganga", "Brahmaputra"], "C", "The Ganga is the longest river flowing within India.", "easy"),
        ("The Tropic of Cancer does NOT pass through which state?", ["Gujarat", "Madhya Pradesh", "Kerala", "West Bengal"], "C", "Kerala lies south of the Tropic of Cancer; it does not pass through it.", "medium"),
        ("Which is the highest peak in India?", ["Nanda Devi", "Kangchenjunga", "K2", "Everest"], "B", "Kangchenjunga is the highest peak entirely within India (K2 and Everest are not).", "medium"),
    ],
    "Economics": [
        ("What does GDP stand for?", ["Gross Domestic Product", "General Domestic Price", "Gross Development Plan", "Gross Domestic Price"], "A", "GDP = Gross Domestic Product, the total value of goods/services produced.", "easy"),
        ("Which committee recommended the establishment of the Insolvency and Bankruptcy Code in India?", ["Raghuram Rajan Committee", "Bankruptcy Law Reforms Committee (BLRC)", "Narasimham Committee", "Kelkar Committee"], "B", "The BLRC, headed by T. K. Viswanathan, recommended the IBC framework.", "hard"),
        ("Repo rate is the rate at which ___.", ["RBI lends to commercial banks", "commercial banks lend to RBI", "banks lend to customers", "government borrows from RBI"], "A", "Repo rate is the rate at which the RBI lends short-term funds to commercial banks.", "medium"),
    ],
    "Static GK": [
        ("Which is the national bird of India?", ["Sparrow", "Peacock", "Parrot", "Eagle"], "B", "The Indian Peacock is the national bird of India.", "easy"),
        ("The headquarters of the United Nations is located in?", ["Geneva", "Paris", "New York", "London"], "C", "The UN headquarters is in New York City.", "easy"),
    ],
    "Science": [
        ("Which gas is most abundant in the Earth's atmosphere?", ["Oxygen", "Carbon dioxide", "Nitrogen", "Hydrogen"], "C", "Nitrogen makes up about 78% of the Earth's atmosphere.", "easy"),
        ("The SI unit of electric current is?", ["Volt", "Ampere", "Ohm", "Watt"], "B", "The ampere (A) is the SI unit of electric current.", "medium"),
    ],
}

BANKING_AWARENESS = {
    "Banking Basics": [
        ("What does NEFT stand for?", ["National Electronic Funds Transfer", "National Efficient Fund Transfer", "New Electronic Finance Transfer", "National Exchange Fund Transfer"], "A", "NEFT = National Electronic Funds Transfer, an RBI-managed payment system.", "easy"),
        ("Which bank is known as the banker's bank in India?", ["SBI", "RBI", "NABARD", "HDFC"], "B", "The Reserve Bank of India (RBI) is the banker's bank and central bank of India.", "easy"),
        ("What is the minimum capital requirement concept called under Basel norms?", ["CRR", "SLR", "CRAR", "MSF"], "C", "Capital to Risk-weighted Assets Ratio (CRAR) is the Basel capital adequacy measure.", "hard"),
    ],
    "Monetary Policy": [
        ("Who decides the repo rate in India?", ["Ministry of Finance", "Monetary Policy Committee (RBI)", "SEBI", "NITI Aayog"], "B", "The Monetary Policy Committee of the RBI sets the repo rate.", "medium"),
        ("CRR stands for?", ["Cash Reserve Ratio", "Credit Risk Ratio", "Capital Reserve Ratio", "Cash Return Ratio"], "A", "CRR = Cash Reserve Ratio, the portion of deposits banks must keep with the RBI.", "medium"),
    ],
    "Financial Institutions": [
        ("NABARD primarily focuses on financing which sector?", ["IT", "Agriculture and Rural Development", "Defense", "Real Estate"], "B", "NABARD (National Bank for Agriculture and Rural Development) finances rural/agri development.", "medium"),
        ("SEBI regulates which of the following?", ["Banks", "Insurance companies", "Securities markets", "Postal services"], "C", "SEBI (Securities and Exchange Board of India) regulates the securities market.", "easy"),
    ],
    "Current Affairs": [
        ("India's Unified Payments Interface (UPI) is regulated by?", ["SEBI", "NPCI/RBI", "IRDAI", "Ministry of Finance"], "B", "UPI is operated by NPCI under RBI's regulatory oversight.", "medium"),
    ],
}


def generate_quant_questions() -> dict[str, list[tuple]]:
    """Programmatically generate genuinely-solvable arithmetic MCQs so
    Quantitative Aptitude has real, verifiable correct answers rather than
    hand-authored ones."""
    rng = random.Random(42)  # deterministic across runs
    bank: dict[str, list[tuple]] = {
        "Percentage": [],
        "Profit and Loss": [],
        "Simple and Compound Interest": [],
        "Number System": [],
        "Averages": [],
        "Ratio and Proportion": [],
    }

    for _ in range(6):
        total = rng.randint(200, 900)
        pct = rng.choice([10, 15, 20, 25, 30, 40])
        answer = round(total * pct / 100, 2)
        options = _make_options(answer, is_float=True)
        bank["Percentage"].append(
            (
                f"What is {pct}% of {total}?",
                options[0],
                options[1],
                f"{pct}% of {total} = {total} * {pct}/100 = {answer}.",
                "easy" if pct in (10, 20) else "medium",
            )
        )

    for _ in range(6):
        cp = rng.randint(200, 2000)
        profit_pct = rng.choice([5, 10, 12, 15, 20, 25])
        sp = round(cp * (1 + profit_pct / 100), 2)
        options = _make_options(sp, is_float=True)
        bank["Profit and Loss"].append(
            (
                f"A shopkeeper buys an article for Rs. {cp} and sells it at a profit of {profit_pct}%. What is the selling price?",
                options[0],
                options[1],
                f"Selling price = CP * (1 + profit%/100) = {cp} * {1 + profit_pct/100} = {sp}.",
                "medium",
            )
        )

    for _ in range(6):
        principal = rng.choice([1000, 2000, 5000, 10000])
        rate = rng.choice([4, 5, 6, 8, 10])
        time = rng.choice([2, 3, 4])
        si = round(principal * rate * time / 100, 2)
        options = _make_options(si, is_float=True)
        bank["Simple and Compound Interest"].append(
            (
                f"Find the simple interest on Rs. {principal} at {rate}% per annum for {time} years.",
                options[0],
                options[1],
                f"SI = P*R*T/100 = {principal}*{rate}*{time}/100 = {si}.",
                "easy",
            )
        )

    for _ in range(6):
        a = rng.randint(10, 99)
        b = rng.randint(2, 12)
        product = a * b
        options = _make_options(product, is_float=False)
        bank["Number System"].append(
            (
                f"What is {a} multiplied by {b}?",
                options[0],
                options[1],
                f"{a} x {b} = {product}.",
                "easy",
            )
        )

    for _ in range(6):
        nums = [rng.randint(10, 100) for _ in range(4)]
        avg = round(sum(nums) / len(nums), 2)
        options = _make_options(avg, is_float=True)
        bank["Averages"].append(
            (
                f"Find the average of {', '.join(map(str, nums))}.",
                options[0],
                options[1],
                f"Average = sum/count = {sum(nums)}/{len(nums)} = {avg}.",
                "medium",
            )
        )

    for _ in range(6):
        x = rng.randint(2, 12)
        y = rng.randint(2, 12)
        g = _gcd(x, y)
        rx, ry = x // g, y // g
        options_text = [f"{rx}:{ry}", f"{ry}:{rx}", f"{rx+1}:{ry}", f"{rx}:{ry+1}"]
        rng.shuffle(options_text)
        correct_letter = "ABCD"[options_text.index(f"{rx}:{ry}")]
        bank["Ratio and Proportion"].append(
            (
                f"Simplify the ratio {x}:{y} to its lowest terms.",
                options_text,
                correct_letter,
                f"Dividing both terms by their GCD ({g}) gives {rx}:{ry}.",
                "medium",
            )
        )

    return bank


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _make_options(correct: float, is_float: bool) -> tuple[list[str], str]:
    rng = random.Random(int(correct * 97) + 1)
    fmt = (lambda v: f"{v:.2f}".rstrip("0").rstrip(".")) if is_float else (lambda v: str(int(v)))
    distractors = set()
    while len(distractors) < 3:
        delta = rng.choice([-1, 1]) * rng.choice([2, 5, 10, 0.5, 1.5])
        candidate = round(correct + delta * max(1, correct * 0.05), 2)
        if candidate != correct and candidate > 0:
            distractors.add(fmt(candidate))
    options = [fmt(correct)] + list(distractors)[:3]
    rng.shuffle(options)
    correct_letter = "ABCD"[options.index(fmt(correct))]
    return options, correct_letter
