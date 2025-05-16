# Distanzschätzung mit Histogramm – mathematischer Kern

---

## 1&nbsp; Diskretisierung der Zufallsgrößen  

| Größe | Symbol | Binning |
|-------|--------|---------|
| Bearing | $\Theta$ | Sektoren der Breite $\Delta_\theta$ (z. B. $5^\circ$) – Index $i$ |
| $|\,$Bearing-Rate$|$ | $|\Omega|$ | feste Ränder $0=\omega_0<\dots<\omega_J$ – Index $j$ |
| Distanz | $R$ | Ringe $\Delta_r$ bis $R_\text{max}$ – Index $k$ |

$\displaystyle
i = \Bigl\lfloor\frac{\Theta}{\Delta_\theta}\Bigr\rfloor,
\quad
j = \max\{n:\; \omega_n \le |\Omega| < \omega_{n+1}\},
\quad
k = \Bigl\lfloor\frac{R}{\Delta_r}\Bigr\rfloor
$

---

## 2  Histogramm der Beobachtungen

Definiere einen Zähl-Tensor. 

$N_{ijk}\;{\in}\;\mathbb N^{I\times J\times K}.$


Für jede Beobachtung erhöhe:

$
N_{ijk}\;=\;N_{ijk}+1
\quad
\text{mit }(i,j,k)\text{ aus Schritt 1.}
$


---

## 3&nbsp; Bedingte Wahrscheinlichkeit  

Gesamtsumme eines $\bigl(i,j\bigr)$-Kastens  

$$
S_{ij}= \sum_{k=0}^{K-1} N_{ijk}
$$

Normierung zur bedingten PDF  

$$
P\!\bigl(R=r_k \mid \Theta\in\theta_i,\;|\Omega|\in\omega_j\bigr)
=\frac{N_{ijk}}{S_{ij}}, \qquad S_{ij}>0
$$

$$
\sum_{k=0}^{K-1} P(R=r_k \mid \theta_i,\omega_j)=1
$$

---

## 4  Lookup  

* Eingabe: aktuelles $(\theta,\omega)$  
* Ausgabe: Vektor **rangeVec** ($r_k$) & **probVec** ($P_{ijk}$)

Erwartungswert:  
$\displaystyle \mathbb{E}[R]=\sum_k r_k\,P_{ijk}$

Quantile: kumulative Summe von **probVec**.