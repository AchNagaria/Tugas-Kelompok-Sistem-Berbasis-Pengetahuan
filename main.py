import json
import os

# ------------------------
# Config
# ------------------------
FACTS_FILE = "facts.json"
RULES_FILE = "rules.json"

# ------------------------
# Warna terminal
# ------------------------
class C:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

# ------------------------
# Load / Save utils
# ------------------------
def load_facts():
    if not os.path.exists(FACTS_FILE):
        return {}
    with open(FACTS_FILE, "r") as f:
        return json.load(f)

def load_rules():
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE, "r") as f:
        return json.load(f)

def save_rules(rules):
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=4)

def generate_rule_id(rules):
    nums = [int(r["id"][1:]) for r in rules if isinstance(r.get("id",""), str) and r["id"].startswith("R")]
    return f"R{(max(nums)+1) if nums else 1}"

# ------------------------
# Validasi helper
# ------------------------
def valid_variable_token(token, facts):
    token = token.strip().upper()
    return token in facts

def parse_var_list(text):
    # menerima teks seperti "A, c, D" -> ["A","C","D"]
    return [t.strip().upper() for t in text.split(",") if t.strip()]

# ------------------------
# CRUD Rules
# ------------------------
def create_rule(facts):
    rules = load_rules()
    rid = generate_rule_id(rules)
    print(C.YELLOW + "\n=== TAMBAH RULE ===" + C.RESET)
    print("Gunakan variabel A-L untuk kondisi. Contoh: A,B,C")
    cond_text = input("Masukkan kondisi (pisah koma): ").strip()
    if not cond_text:
        print(C.RED + "Kondisi tidak boleh kosong." + C.RESET)
        return
    conds = parse_var_list(cond_text)
    invalid = [c for c in conds if not valid_variable_token(c, facts)]
    if invalid:
        print(C.RED + f"Variabel tidak valid: {invalid}. Gunakan A-L." + C.RESET)
        return

    then = input("Masukkan kesimpulan (organik/anorganik/b3): ").strip().lower()
    if then not in ["organik", "anorganik", "b3"]:
        print(C.RED + "Kesimpulan harus salah satu dari: organik, anorganik, b3" + C.RESET)
        return

    desc = input("Deskripsi (opsional): ").strip()

    new_rule = {"id": rid, "if": conds, "then": then, "description": desc}
    rules.append(new_rule)
    save_rules(rules)
    print(C.GREEN + f"✔ Rule {rid} tersimpan." + C.RESET)

def read_rules():
    rules = load_rules()
    print(C.YELLOW + "\n=== DAFTAR RULE ===" + C.RESET)
    if not rules:
        print("(belum ada rule)")
        return
    for r in rules:
        print(f"{C.GREEN}{r['id']}{C.RESET}: IF {r['if']} THEN {r['then']} — {r.get('description','')}")
    print()

def update_rule(facts):
    rules = load_rules()
    read_rules()
    rid = input("Masukkan ID rule yang ingin diupdate: ").strip().upper()
    rule = next((r for r in rules if r["id"] == rid), None)
    if not rule:
        print(C.RED + "Rule tidak ditemukan." + C.RESET)
        return

    print(C.YELLOW + "Kosongkan input untuk tidak mengubah kolom tersebut." + C.RESET)
    cond_text = input(f"Kondisi baru [{','.join(rule['if'])}]: ").strip()
    if cond_text:
        conds = parse_var_list(cond_text)
        invalid = [c for c in conds if not valid_variable_token(c, facts)]
        if invalid:
            print(C.RED + f"Variabel tidak valid: {invalid}" + C.RESET)
            return
        rule["if"] = conds

    then_text = input(f"Kesimpulan baru [{rule['then']}]: ").strip().lower()
    if then_text:
        if then_text not in ["organik", "anorganik", "b3"]:
            print(C.RED + "Kesimpulan harus salah satu dari: organik, anorganik, b3" + C.RESET)
            return
        rule["then"] = then_text

    desc_text = input(f"Deskripsi baru [{rule.get('description','')}]: ").strip()
    if desc_text != "":
        rule["description"] = desc_text

    save_rules(rules)
    print(C.GREEN + f"✔ Rule {rid} diperbarui." + C.RESET)

def delete_rule():
    rules = load_rules()
    read_rules()
    rid = input("Masukkan ID rule yang ingin dihapus: ").strip().upper()
    rule = next((r for r in rules if r["id"] == rid), None)
    if not rule:
        print(C.RED + "Rule tidak ditemukan." + C.RESET)
        return
    confirm = input(f"Ketik YA untuk menghapus {rid}: ").strip().upper()
    if confirm != "YA":
        print(C.YELLOW + "Dibatalkan." + C.RESET)
        return
    new_rules = [r for r in rules if r["id"] != rid]
    save_rules(new_rules)
    print(C.GREEN + f"✔ Rule {rid} dihapus." + C.RESET)

# ------------------------
# Forward chaining (tanpa priority)
# ------------------------
def forward_chaining(facts_input, rules, facts):
    # facts_input: list of variable tokens ["A","C"]
    facts = set([f.strip().upper() for f in facts_input if f.strip()])
    # validate initial facts
    invalid = [f for f in facts if f not in facts]
    if invalid:
        return {"error": f"Variabel fakta tidak valid: {invalid}"}

    applied = []
    new_facts = []

    # rules is list of dicts with 'id','if','then'
    while True:
        activated_any = False
        for rule in rules:
            conds = set([c.strip().upper() for c in rule.get("if", [])])
            if conds.issubset(facts) and rule["id"] not in applied:
                applied.append(rule["id"])
                # THEN bisa berupa kategori (organik/anorganik/b3) atau variabel lain
                then_val = rule["then"]
                # standar: jika then berupa huruf variabel -> tambahkan sebagai fakta,
                # jika then berupa kategori (organik/anorganik/b3) tambahkan juga sebagai fakta
                facts.add(then_val)
                new_facts.append(then_val)
                activated_any = True
                print(f"{C.GREEN}Step {len(applied)} → {rule['id']} aktif → menghasilkan: {then_val}{C.RESET}")
                break
        if not activated_any:
            break

    # cari kategori akhir
        # Tentukan kategori akhir berdasarkan prioritas
    kategori = None
    priority_map = {"b3": 1, "anorganik": 2, "organik": 3}

    # Ambil semua kategori yang muncul dalam fakta
    detected = [t for t in ["organik", "anorganik", "b3"] if t in facts]

    if detected:
        kategori = min(detected, key=lambda x: priority_map[x])


    return {
        "initial_facts": sorted(list(set(facts_input))),
        "new_facts": new_facts,
        "applied_rules": applied,
        "final_category": kategori
    }

# ------------------------
# Identify wrapper
# ------------------------
def identify(facts):
    rules = load_rules()
    if not rules:
        print(C.YELLOW + "Belum ada rule. Tambahkan rule dulu." + C.RESET)
        return

    print(C.YELLOW + "\n=== IDENTIFIKASI SAMPAH ===" + C.RESET)
    print("Variabel yang tersedia:")
    for k, v in facts.items():
        print(f"{k} = {v}")
    fak = input("\nMasukkan fakta awal (contoh: A,C,D): ").strip()
    if not fak:
        print(C.RED + "Fakta tidak boleh kosong." + C.RESET)
        return
    facts = parse_var_list(fak)
    result = forward_chaining(facts, rules, facts)
    if isinstance(result, dict) and result.get("error"):
        print(C.RED + result["error"] + C.RESET)
        return

    print(C.YELLOW + "\n=== RINGKASAN ===" + C.RESET)
    print("Fakta Awal :", result["initial_facts"])
    print("Fakta Baru :", result["new_facts"])
    print("Rule yang aktif:", result["applied_rules"])
    if result["final_category"]:
        print(C.GREEN + f"\nKesimpulan akhir: Sampah termasuk kategori → {result['final_category'].upper()}" + C.RESET)
    else:
        print(C.RED + "\nTidak menemukan kategori sampah." + C.RESET)

# ------------------------
# Menu utama
# ------------------------
def menu():
    facts = load_facts()
    if not facts:
        print(C.RED + f"File {FACTS_FILE} tidak ditemukan atau kosong. Buat file facts.json dulu." + C.RESET)
        return

    while True:
        print("""
========================================
 SISTEM PAKAR IDENTIFIKASI SAMPAH (A-L)
========================================
1. Tambah Rule
2. Lihat Rule
3. Update Rule
4. Hapus Rule
5. Identifikasi Sampah
0. Keluar
""")
        pilihan = input("Pilih menu: ").strip()
        if pilihan == "1":
            create_rule(facts)
        elif pilihan == "2":
            read_rules()
        elif pilihan == "3":
            update_rule(facts)
        elif pilihan == "4":
            delete_rule()
        elif pilihan == "5":
            identify(facts)
        elif pilihan == "0":
            print("Keluar...")
            break
        else:
            print(C.RED + "Pilihan tidak valid." + C.RESET)

if __name__ == "__main__":
    menu()
