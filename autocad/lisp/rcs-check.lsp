;;; rcs-check.lsp -- RCS-laagcontrole + ruimtelijst (les 21, oefenplattegrond, fictief)
;;; ⚠️ niet in AutoCAD uitgevoerd (AutoCAD staat niet op de Mac van de lesmaker).
;;;
;;; Gebruik in AutoCAD:  (load "C:/pad/naar/rcs-check.lsp")  en dan  RCSCHECK
;;; Alleen basis-AutoLISP (tblnext, ssget, entget, wcmatch, open/write-line): geen vla-/vlax-/vl-,
;;; zodat het ook in accoreconsole kan draaien (geen COM daar; zie feiten-rvb-autocad.md, B).
;;;
;;; Regels (gelijk aan python-ezdxf/rcs_check.py, de referentie):
;;;  1. laagnaam = 2 cijfers + spatie + omschrijving (A-Z a-z 0-9 spatie - _); 0 en Defpoints uitgezonderd
;;;  2. geen lege lagen: minstens 1 entiteit in modelspace (0 en Defpoints uitgezonderd)
;;;  3. laag 0: alleen INSERT
;;;  4. ruimtelijst: elke LWPOLYLINE op "92 Rust- en werkgebieden"; nummer = TEXT "##.##" op die laag
;;;     waarvan het invoegpunt (groep 10) binnen de contour ligt.
;;;
;;; BEKENDE BEPERKING: de oppervlakte is de shoelace-formule over de vertices (groep 10).
;;; Bulges (groep 42, boogsegmenten) worden GENEGEERD: een ruimte met een gebogen wand krijgt de
;;; oppervlakte van de koordenveelhoek. Zie uitvoer/ezdxf-bulge-demo.txt: 24.00 m2 zonder, 26.80 m2 met bulge.
;;; (Met vla-get-area zou het wel kloppen, maar dat is COM en werkt niet in accoreconsole.)
;;; Verder: alleen LWPOLYLINE (geen oude 2D POLYLINE); coordinaten in OCS = WCS bij normaal (0 0 1).

(setq *rcs-ruimtelaag* "92 Rust- en werkgebieden")

(defun rcs:teken-ok (c)
  ;; c = ascii-code; toegestaan: 0-9 A-Z a-z spatie - _
  (or (and (>= c 48) (<= c 57)) (and (>= c 65) (<= c 90)) (and (>= c 97) (<= c 122))
      (= c 32) (= c 45) (= c 95)))

(defun rcs:laagnaam-ok (naam / i ok)
  ;; wcmatch "#*": eerste teken is een cijfer; de rest per teken
  (setq ok (and (> (strlen naam) 3)
                (wcmatch naam "##*")
                (= (ascii (substr naam 3 1)) 32)))
  (setq i 4)
  (while (and ok (<= i (strlen naam)))
    (setq ok (rcs:teken-ok (ascii (substr naam i 1))) i (1+ i)))
  ok)

(defun rcs:aantal (filter / ss)
  ;; aantal entiteiten in modelspace dat aan het filter voldoet (410 = layout "Model")
  (setq ss (ssget "X" (append (list (cons 410 "Model")) filter)))
  (if ss (sslength ss) 0))

(defun rcs:vertices (ed / pts)
  ;; alle groep-10-punten van een LWPOLYLINE als (x y)
  (foreach g ed
    (if (= (car g) 10) (setq pts (cons (list (cadr g) (caddr g)) pts))))
  (reverse pts))

(defun rcs:shoelace (pts / som i n p q)
  ;; |sum(x_i*y_i+1 - x_i+1*y_i)| / 2, in tekeningeenheden^2 (mm2). Bulges genegeerd.
  (setq som 0.0 i 0 n (length pts))
  (while (< i n)
    (setq p (nth i pts) q (nth (rem (1+ i) n) pts)
          som (+ som (- (* (car p) (cadr q)) (* (car q) (cadr p))))
          i (1+ i)))
  (/ (abs som) 2.0))

(defun rcs:binnen (pt pts / res i j xi yi xj yj x y)
  ;; ray casting, zoals binnen() in rcs_check.py
  (setq x (car pt) y (cadr pt) res nil j (1- (length pts)) i 0)
  (while (< i (length pts))
    (setq xi (car (nth i pts)) yi (cadr (nth i pts))
          xj (car (nth j pts)) yj (cadr (nth j pts)))
    (if (and (/= (> yi y) (> yj y))
             (< x (+ (/ (* (- xj xi) (- y yi)) (- yj yi)) xi)))
      (setq res (not res)))
    (setq j i i (1+ i)))
  res)

(defun rcs:meld (f tekst)
  (princ (strcat "\n" tekst))
  (if f (write-line tekst f)))

(defun c:RCSCHECK (/ lg naam fouten ss i ed nrs pts gev nr gesloten csv f txt opp)
  (setq fouten 0
        txt (strcat (getvar "DWGPREFIX") (substr (getvar "DWGNAME") 1 (- (strlen (getvar "DWGNAME")) 4)))
        f (open (strcat txt "-rcscheck.txt") "w")
        csv (open (strcat txt "-ruimten.csv") "w"))
  (rcs:meld f (strcat "RCSCHECK (AutoLISP) op " (getvar "DWGNAME")))
  ;; 1 + 2: laagtabel doorlopen
  (rcs:meld f "-- Laagnamen en lege lagen --")
  (setq lg (tblnext "LAYER" T))
  (while lg
    (setq naam (cdr (assoc 2 lg)))
    (if (not (member (strcase naam) '("0" "DEFPOINTS")))
      (progn
        (if (not (rcs:laagnaam-ok naam))
          (progn (rcs:meld f (strcat "FOUT laagnaam: '" naam "' voldoet niet aan '## omschrijving'"))
                 (setq fouten (1+ fouten))))
        (if (= 0 (rcs:aantal (list (cons 8 naam))))
          (progn (rcs:meld f (strcat "FOUT lege laag: '" naam "'"))
                 (setq fouten (1+ fouten))))))
    (setq lg (tblnext "LAYER")))
  ;; 3: laag 0 alleen INSERT  (-4 filter: alles op laag 0 dat geen INSERT is)
  (rcs:meld f "-- Laag 0 --")
  (setq ss (ssget "X" '((410 . "Model") (8 . "0") (-4 . "<NOT") (0 . "INSERT") (-4 . "NOT>"))))
  (if ss
    (progn (setq i 0)
      (while (< i (sslength ss))
        (setq ed (entget (ssname ss i)))
        (rcs:meld f (strcat "FOUT laag 0 bevat " (cdr (assoc 0 ed)) " (handle " (cdr (assoc 5 ed)) ")"))
        (setq fouten (1+ fouten) i (1+ i)))))
  ;; 4: ruimtenummers (TEXT ##.## op laag 92) verzamelen; ` maakt de punt letterlijk in wcmatch
  (setq nrs nil ss (ssget "X" (list '(410 . "Model") '(0 . "TEXT") (cons 8 *rcs-ruimtelaag*))))
  (if ss
    (progn (setq i 0)
      (while (< i (sslength ss))
        (setq ed (entget (ssname ss i)))
        (if (wcmatch (cdr (assoc 1 ed)) "##`.##")
          (setq nrs (cons (list (cdr (assoc 1 ed)) (cdr (assoc 10 ed))) nrs)))
        (setq i (1+ i)))))
  (rcs:meld f "-- Ruimtelijst (laag 92) --")
  (rcs:meld f "nummer;handle;gesloten;opp_m2_zonder_bulge")
  (write-line "nummer;handle;gesloten;opp_m2_zonder_bulge" csv)
  (setq ss (ssget "X" (list '(410 . "Model") '(0 . "LWPOLYLINE") (cons 8 *rcs-ruimtelaag*))))
  (if ss
    (progn (setq i 0)
      (while (< i (sslength ss))
        (setq ed (entget (ssname ss i))
              pts (rcs:vertices ed)
              gesloten (= 1 (logand 1 (cdr (assoc 70 ed))))
              gev nil)
        (foreach n (reverse nrs)
          (if (rcs:binnen (cadr n) pts) (setq gev (cons (car n) gev))))
        (setq nr (cond ((= (length gev) 1) (car gev)) ((null gev) "?") (T "meerdere")))
        (if (/= (length gev) 1)
          (progn (rcs:meld f (strcat "FOUT ruimte " (cdr (assoc 5 ed)) ": "
                                     (itoa (length gev)) " ruimtenummers in contour"))
                 (setq fouten (1+ fouten))))
        (if gesloten
          (setq opp (rtos (/ (rcs:shoelace pts) 1.0e6) 2 2))
          (progn (rcs:meld f (strcat "FOUT ruimte " (cdr (assoc 5 ed)) " (" nr "): polyline niet gesloten"))
                 (setq fouten (1+ fouten) opp "")))
        (setq txt (strcat nr ";" (cdr (assoc 5 ed)) ";" (if gesloten "ja" "nee") ";" opp))
        (rcs:meld f txt)
        (write-line txt csv)
        (setq i (1+ i)))))
  (rcs:meld f (strcat "Klaar: " (itoa fouten) " bevinding(en)."))
  (close f)
  (close csv)
  (princ))

(princ "\nrcs-check.lsp geladen. Typ RCSCHECK.")
(princ)
