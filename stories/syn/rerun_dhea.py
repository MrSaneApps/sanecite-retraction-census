"""J Ovarian Res 2025 (PMC11843996) fig 2B clinical pregnancy, OR M-H fixed. Retracted trial: Zhang 2021
(Evid Based Complement Alternat Med, retracted 2023). Transcribed from dhea-fig2.jpg."""
import math
def or_mh(rows):
    R=sum(a*d/(a+b+c+d) for _,a,n1,c,n2 in rows for b,d in [(n1-a,n2-c)])
    S=sum(b*c/(a+b+c+d) for _,a,n1,c,n2 in rows for b,d in [(n1-a,n2-c)])
    P=sum((a+d)/(n1+n2)*a*d/(n1+n2) for _,a,n1,c,n2 in rows for b,d in [(n1-a,n2-c)])
    PS=sum(((a+d)/(n1+n2)*b*c+(b+c)/(n1+n2)*a*d)/(n1+n2) for _,a,n1,c,n2 in rows for b,d in [(n1-a,n2-c)])
    Q=sum((b+c)/(n1+n2)*b*c/(n1+n2) for _,a,n1,c,n2 in rows for b,d in [(n1-a,n2-c)])
    o=R/S; v=P/(2*R*R)+PS/(2*R*S)+Q/(2*S*S); se=math.sqrt(v); m=math.log(o)
    return o, math.exp(m-1.96*se), math.exp(m+1.96*se), math.erfc(abs(m/se)/math.sqrt(2))
B=[("Fu 2017",8,58,4,58),("Kara 2014",33,104,34,104),("Kotb 2016",23,70,11,70),("Li 2021",6,20,4,25),("Moawad 2012",12,58,8,47),
   ("Mostajeran 2018",21,45,18,49),("Narkwichean 2017",8,27,9,25),("Tartagni 2015",22,53,18,56),("Wang 2022",38,269,42,274),
   ("Wiser 2010",7,26,3,25),("Yeung 2014",3,16,4,16),("Yeung 2015",10,36,14,36),("Yuan 2016",30,117,12,102),("Zhang 2014",8,42,7,53),("Zhang 2021",8,33,3,35)]
for lab,rows in [("published 1.34 [1.08,1.67]",B),("without Zhang 2021",[r for r in B if r[0]!="Zhang 2021"])]:
    o,l,h,p=or_mh(rows); print(f"{lab}: OR {o:.2f} [{l:.2f}, {h:.2f}] p={p:.3f}")
