"use strict";

// Mini self-check dla zip.js (format binarny — wart jednego uruchamialnego
// testu). Weryfikacja niezależnym czytnikiem (Python zipfile), nie naszym
// własnym kodem — inaczej test i implementacja mogłyby dzielić ten sam błąd.

const assert = require("assert");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { budujZip } = require("./zip");

const dane1 = Buffer.from("Zawartość pliku jeden — ąćęłńóśźż", "utf-8");
const dane2 = Buffer.from("x".repeat(5000), "utf-8");
const zip = budujZip([
  { nazwa: "raport.docx", dane: dane1 },
  { nazwa: "wynik_tabele_Punkt1.xlsx", dane: dane2 },
]);

const tmpZip = path.join(os.tmpdir(), `test_zip_${Date.now()}.zip`);
fs.writeFileSync(tmpZip, zip);

const wynik = execFileSync("python3", ["-c", `
import zipfile, sys
z = zipfile.ZipFile(sys.argv[1])
assert z.testzip() is None, "uszkodzone archiwum"
nazwy = z.namelist()
assert nazwy == ["raport.docx", "wynik_tabele_Punkt1.xlsx"], nazwy
assert z.read("raport.docx").decode("utf-8") == open(sys.argv[2], encoding="utf-8").read()
assert len(z.read("wynik_tabele_Punkt1.xlsx")) == 5000
print("OK")
`, tmpZip, "/dev/stdin"], { input: dane1 }).toString();

fs.unlinkSync(tmpZip);
assert.strictEqual(wynik.trim(), "OK");
console.log("OK: zip.js — archiwum czytelne przez python zipfile, nazwy i zawartość zgodne");
