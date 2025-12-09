import json
import os
from typing import List, Dict, Set, Tuple, Any

RULES_FILE = "rules.json"
FACTS_FILE = "facts.json"


# -------------------------------------------------
# Utility - 
# -------------------------------------------------
def normalize(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


# -------------------------------------------------
# Rule Model
# -------------------------------------------------
class Rule:
    def __init__(self, rule_id: str, conditions: List[str], conclusion: str,
                 priority: int = 0, description: str = ""):
        self.id = rule_id
        self.conditions = [normalize(c) for c in conditions]
        self.conclusion = normalize(conclusion)
        self.priority = int(priority)
        self.description = description

    def to_dict(self):
        return {
            "id": self.id,
            "conditions": self.conditions,
            "conclusion": self.conclusion,
            "priority": self.priority,
            "description": self.description,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Rule":
        return Rule(
            d["id"],
            d.get("conditions", []),
            d.get("conclusion", ""),
            d.get("priority", 0),
            d.get("description", ""),
        )


# -------------------------------------------------
# Knowledge Base
# -------------------------------------------------
class KnowledgeBase:
    def __init__(self):
        self.rules: Dict[str, Rule] = {}

    def add_rule(self, rule: Rule):
        if rule.id in self.rules:
            return False
        self.rules[rule.id] = rule
        return True

    def get_rule(self, rule_id: str):
        return self.rules.get(rule_id)

    def update_rule(self, rule_id: str, **fields):
        r = self.get_rule(rule_id)
        if not r:
            return False

        if "conditions" in fields:
            new_conditions = [normalize(c) for c in fields["conditions"]]
            if len(new_conditions) == 0:
                return False
            r.conditions = new_conditions

        if "conclusion" in fields:
            if not fields["conclusion"].strip():
                return False
            r.conclusion = normalize(fields["conclusion"])

        if "priority" in fields:
            try:
                r.priority = int(fields["priority"])
            except ValueError:
                return False

        if "description" in fields:
            r.description = fields["description"]

        return True

    def delete_rule(self, rule_id: str):
        if rule_id not in self.rules:
            return False
        del self.rules[rule_id]
        return True

    def list_rules(self) -> List[Rule]:
        return sorted(self.rules.values(), key=lambda r: (-r.priority, r.id))

    def save(self):
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self.list_rules()], f, indent=2)

    def load(self):
        if not os.path.exists(RULES_FILE):
            return False
        try:
            with open(RULES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            print(" File rules.json rusak — membuat baru.")
            self.save()
            return False

        self.rules = {d["id"]: Rule.from_dict(d) for d in data}
        return True


# -------------------------------------------------
# Fact Base
# -------------------------------------------------
class FactBase:
    def __init__(self):
        self.facts: Set[str] = set()

    def add_fact(self, fact: str):
        f = normalize(fact)
        if not f:
            return False
        if f in self.facts:
            return False
        self.facts.add(f)
        return True

    def remove_fact(self, fact: str):
        fact = normalize(fact)
        if fact not in self.facts:
            return False
        self.facts.remove(fact)
        return True

    def list_facts(self):
        return sorted(self.facts)

    def save(self):
        with open(FACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(self.facts), f, indent=2)

    def load(self):
        if not os.path.exists(FACTS_FILE):
            return False
        try:
            with open(FACTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            print(" File facts.json rusak — membuat baru.")
            self.save()
            return False
        self.facts = {normalize(x) for x in data}
        return True


# -------------------------------------------------
# Forward Chaining
# -------------------------------------------------
class ForwardChainer:
    def __init__(self, kb: KnowledgeBase, fb: FactBase):
        self.kb = kb
        self.fb = fb

    def run(self) -> Tuple[Set[str], List[Dict[str, Any]]]:
        inferred = set(self.fb.facts)
        trace = []
        step = 1

        applied = True
        while applied:
            applied = False
            for rule in self.kb.list_rules():
                if all(c in inferred for c in rule.conditions):
                    if rule.conclusion not in inferred:
                        inferred.add(rule.conclusion)
                        trace.append({
                            "step": step,
                            "rule_id": rule.id,
                            "conditions": rule.conditions,
                            "conclusion": rule.conclusion,
                            "priority": rule.priority,
                        })
                        step += 1
                        applied = True

        return inferred, trace

    def classify(self, inferred: Set[str]):
        if "b3" in inferred:
            return "b3"
        if "anorganik" in inferred:
            return "anorganik"
        if "organik" in inferred:
            return "organik"
        return "unknown"


# -------------------------------------------------
# Ensure files exist
# -------------------------------------------------
def ensure_files_exist(kb: KnowledgeBase, fb: FactBase):
    if not kb.load():
        kb.save()
    if not fb.load():
        fb.save()


# -------------------------------------------------
# CLI Display helpers
# -------------------------------------------------
def print_rules(kb: KnowledgeBase):
    print("\nDaftar Aturan:")
    if not kb.rules:
        print("- (kosong)")
        return
    for r in kb.list_rules():
        cond = ", ".join(r.conditions)
        print(f"- {r.id}: IF [{cond}] THEN {r.conclusion} (prio={r.priority})")


def print_facts(fb: FactBase):
    print("\nFakta:")
    if not fb.facts:
        print("- (kosong)")
        return
    for f in fb.list_facts():
        print(f"- {f}")


def infer_and_show(kb: KnowledgeBase, fb: FactBase):
    if not fb.facts:
        print("\n Tidak bisa inferensi: fakta kosong.")
        return
    if not kb.rules:
        print("\n Tidak bisa inferensi: aturan kosong.")
        return

    ch = ForwardChainer(kb, fb)
    inferred, trace = ch.run()
    final = ch.classify(inferred)

    print("\n=== HASIL INFERENSI ===")
    print("Fakta awal:", fb.list_facts())
    print("Fakta akhir:", sorted(inferred))

    print("\nJejak aturan:")
    if not trace:
        print("- Tidak ada aturan yang diaplikasikan")
    else:
        for t in trace:
            cond = ", ".join(t["conditions"])
            print(f"Step {t['step']}: Rule {t['rule_id']} ({cond} -> {t['conclusion']})")

    print(f"\nHASIL AKHIR = {final.upper()}\n")


# -------------------------------------------------
# Main Menu
# -------------------------------------------------
def main():
    kb = KnowledgeBase()
    fb = FactBase()
    ensure_files_exist(kb, fb)

    while True:
        print("\n===== SISTEM PAKAR SAMPAH =====")
        print("1. Tampilkan Aturan")
        print("2. Tambah Aturan")
        print("3. Hapus Aturan")
        print("4. Update Aturan")
        print("5. Tampilkan Fakta")
        print("6. Tambah Fakta")
        print("7. Hapus Fakta")
        print("8. Jalankan Inferensi")
        print("0. Keluar")

        pilih = input("Pilih menu: ").strip()

        if pilih == "1":
            print_rules(kb)

        elif pilih == "2":
            rid = input("ID aturan: ").strip()
            if not rid:
                print(" ID tidak boleh kosong.")
                continue

            if kb.get_rule(rid):
                print(" ID sudah ada.")
                continue

            cond_raw = input("Conditions (koma): ").strip()
            if not cond_raw:
                print(" Conditions tidak boleh kosong.")
                continue
            conditions = [c.strip() for c in cond_raw.split(",") if c.strip()]

            conclusion = input("Conclusion: ").strip()
            if not conclusion:
                print(" Conclusion tidak boleh kosong.")
                continue

            prio_raw = input("Priority: ").strip()
            try:
                prio = int(prio_raw)
            except ValueError:
                print(" Priority harus angka.")
                continue

            desc = input("Deskripsi: ")

            if kb.add_rule(Rule(rid, conditions, conclusion, prio, desc)):
                kb.save()
                print("Aturan ditambahkan.")
            else:
                print(" Gagal menambah aturan.")

        elif pilih == "3":
            rid = input("ID aturan: ").strip()
            if kb.delete_rule(rid):
                kb.save()
                print("Aturan dihapus.")
            else:
                print(" Aturan tidak ditemukan.")

        elif pilih == "4":
            rid = input("ID aturan: ").strip()
            if not kb.get_rule(rid):
                print(" Aturan tidak ditemukan.")
                continue

            cond = input("Conditions baru (kosong=skip): ").strip()
            concl = input("Conclusion baru (kosong=skip): ").strip()
            prio = input("Priority baru (kosong=skip): ").strip()
            desc = input("Deskripsi baru (kosong=skip): ").strip()

            fields = {}
            if cond:
                c = [x.strip() for x in cond.split(",") if x.strip()]
                if len(c) == 0:
                    print(" Conditions tidak boleh kosong.")
                    continue
                fields["conditions"] = c

            if concl:
                fields["conclusion"] = concl

            if prio:
                try:
                    fields["priority"] = int(prio)
                except ValueError:
                    print(" Priority harus angka.")
                    continue

            if desc:
                fields["description"] = desc

            if kb.update_rule(rid, **fields):
                kb.save()
                print("Aturan diperbarui.")
            else:
                print(" Update gagal — periksa input.")

        elif pilih == "5":
            print_facts(fb)

        elif pilih == "6":
            f = input("Fakta baru: ").strip()
            if fb.add_fact(f):
                fb.save()
                print("Fakta ditambah.")
            else:
                print(" Gagal: fakta kosong atau sudah ada.")

        elif pilih == "7":
            f = input("Fakta dihapus: ").strip()
            if fb.remove_fact(f):
                fb.save()
                print("Fakta dihapus.")
            else:
                print(" Fakta tidak ditemukan.")

        elif pilih == "8":
            infer_and_show(kb, fb)

        elif pilih == "0":
            break

        else:
            print(" Pilihan tidak valid.")


if __name__ == "__main__":
    main()
