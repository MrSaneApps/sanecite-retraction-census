"""BMC Pediatr 2024 (PMC10858564): nifedipine + sildenafil vs nifedipine. Retracted trial: Maher 2019 BJOG.
Numbers transcribed from the review's forest plots (sild-*.jpg)."""
import sys; sys.path.insert(0, "..")
from meta import *
D = "Maher 2019"
report("Fig 2 prolongation of pregnancy (days), MD IV random", md, [
    ("Hassan 2023", 17.58, 10.65, 80, 10.58, 8.99, 80), ("Maher 2019", 33.78, 22.03, 121, 20.86, 21.14, 118),
    ("Mohammadi 2021", 16.17, 5.14, 66, 9.98, 3.5, 66), ("Singh 2023", 9.26, 5.33, 30, 2.77, 1.01, 30)], D, "6.99 [5.32, 8.65]")
report("Fig 3 delivery within 24-72 h, RR M-H fixed (all 12 rows)", rr_mh_fixed, [
    ("El-Sayed 24", 5, 48, 11, 48), ("Maher 2019", 6, 121, 8, 118), ("Mohammadi 24", 3, 66, 2, 66), ("Nasrolahei 24", 3, 63, 5, 63),
    ("El-Sayed 48", 11, 48, 19, 48), ("Hassan 48", 16, 80, 26, 80), ("Maher 2019", 14, 121, 19, 118), ("Mohammadi 48", 4, 66, 5, 66),
    ("Nasrolahei 48", 6, 63, 9, 63), ("El-Sayed 72", 13, 48, 24, 48), ("Maher 2019", 22, 121, 37, 118), ("Nasrolahei 72", 8, 63, 13, 63)],
    D, "0.62 [0.50, 0.76]")
report("Fig 4 birth weight (g), MD IV random", md, [
    ("El-Sayed 2023", 2800, 300, 48, 2600, 400, 48), ("Maher 2019", 1874.79, 715.99, 121, 1840.36, 902.91, 118),
    ("Mohammadi 2021", 2154.5, 221.3, 66, 1609, 204.3, 66), ("Nasrolahei 2023", 2167.3, 362.2, 63, 2003.1, 30.8, 63),
    ("Singh 2023", 2381.67, 492.44, 30, 2090, 372.64, 30)], D, "252.48 [40.95, 464.01]")
report("Fig 5 NICU admission, RR M-H fixed", rr_mh_fixed, [
    ("Hassan 2023", 3, 80, 7, 80), ("Maher 2019", 38, 121, 52, 118), ("Mohammadi 2021", 24, 66, 44, 66),
    ("Nasrolahei 2023", 16, 63, 27, 63), ("Singh 2023", 7, 30, 11, 30)], D, "0.62 [0.50, 0.76]")
