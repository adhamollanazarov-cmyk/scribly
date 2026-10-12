"""Independent exact-input solutions of the 20 hard problems; no lesson/eval code.

Signed components use the axes stated in the questions. All circuit currents use
A -> B; powers delivered by ideal emfs are -emf * current. Energy work is signed.
"""

import sympy as s

Reference = dict[str, dict[str, tuple[s.Expr, str, str]]]


def reference_answers() -> Reference:
    r = s.Rational
    g = r("9.81")
    k = 1 / (4 * s.pi * r("8.854e-12"))
    answers: Reference = {}

    def add(key: str, **items: tuple[s.Expr, str, str]) -> None:
        answers[key] = items

    def scalar(value: s.Expr, unit: str) -> tuple[s.Expr, str, str]:
        return value, unit, ""

    def directed(value: s.Expr, unit: str, positive: str) -> tuple[s.Expr, str, str]:
        return value, unit, positive

    # KCL: (V-e1)/r1 + (V-e2)/r2 + V/r3 = 0.
    def circuit(e1: str, e2: str, r1: str, r2: str, r3: str) -> tuple[s.Expr, ...]:
        e, f, a, b, c = map(r, (e1, e2, r1, r2, r3))
        voltage = (e / a + f / b) / (1 / a + 1 / b + 1 / c)
        return voltage, (voltage - e) / a, (voltage - f) / b, voltage / c

    v, i1, i2, i3 = circuit("12", "-9", "3.3", "2.2", "4.7")
    add(
        "hard-kirchhoff-opposed",
        I1=directed(i1, "A", "A->B"),
        I2=directed(i2, "A", "A->B"),
        I3=directed(i3, "A", "A->B"),
    )
    v, i1, i2, i3 = circuit("14", "11.5", "0.60", "0.90", "5.6")
    add(
        "hard-kirchhoff-charging",
        I1=directed(i1, "A", "A->B"),
        I2=directed(i2, "A", "A->B"),
        I_load=directed(i3, "A", "A->B"),
        V_AB=scalar(v, "V"),
        P2=scalar(-r("11.5") * i2, "W"),
    )
    v, i1, i2, i3 = circuit("-6", "4.5", "1.8", "2.7", "3.9")
    add(
        "hard-kirchhoff-potential",
        V_AB=scalar(v, "V"),
        I3=directed(i3, "A", "A->B"),
        I2=directed(i2, "A", "A->B"),
        P3=scalar(i3**2 * r("3.9"), "W"),
    )
    v, i1, i2, i3 = circuit("9", "6", "1.5", "0.50", "2")
    p1, p2 = -9 * i1, -6 * i2
    dissipated = i1**2 * r("1.5") + i2**2 * r("0.5") + i3**2 * 2
    assert s.simplify(p1 + p2 - dissipated) == 0
    add(
        "hard-kirchhoff-power-balance",
        I1=directed(i1, "A", "A->B"),
        I2=directed(i2, "A", "A->B"),
        I3=directed(i3, "A", "A->B"),
        P1=scalar(p1, "W"),
        P2=scalar(p2, "W"),
        P_total=scalar(dissipated, "W"),
    )

    fx = k * r("2e-6") * r("3e-6") / r("0.4") ** 2
    fy = -k * r("2e-6") * r("1.5e-6") / r("0.3") ** 2
    add(
        "hard-vec-coulomb-2d",
        Fx=directed(fx, "N", "+x"),
        Fy=directed(fy, "N", "+y"),
        F=scalar(s.sqrt(fx**2 + fy**2), "N"),
    )
    distance = s.sqrt(r("0.1") ** 2 + r("0.15") ** 2)
    ex = k * r("0.1") * (r("4e-9") + r("2.5e-9")) / distance**3
    ey = k * r("0.15") * (r("4e-9") - r("2.5e-9")) / distance**3
    add(
        "hard-vec-field-2d",
        Ex=directed(ex, "N/C", "+x"),
        Ey=directed(ey, "N/C", "+y"),
        E=scalar(s.sqrt(ex**2 + ey**2), "N/C"),
    )
    rx = r("3.2") * s.cos(25 * s.pi / 180) - r("4.75") * s.sin(40 * s.pi / 180)
    ry = r("3.2") * s.sin(25 * s.pi / 180) + r("4.75") * s.cos(40 * s.pi / 180) - r("1.6")
    add(
        "hard-vec-displacement",
        Rx=directed(rx, "km", "+x"),
        Ry=directed(ry, "km", "+y"),
        R=scalar(s.sqrt(rx**2 + ry**2), "km"),
    )
    vx = r("1.8") + r("3.5") * s.cos(115 * s.pi / 180)
    vy = r("3.5") * s.sin(115 * s.pi / 180)
    t = 85 / vy
    add(
        "hard-vec-river",
        vx=directed(vx, "m/s", "+x"),
        vy=directed(vy, "m/s", "+y"),
        speed=scalar(s.sqrt(vx**2 + vy**2), "m/s"),
        t=scalar(t, "s"),
        drift=directed(vx * t, "m", "+x"),
    )
    ux, uy = r("14.5") * s.cos(32 * s.pi / 180), r("14.5") * s.sin(32 * s.pi / 180)
    t = (uy + s.sqrt(uy**2 + 2 * g * 23)) / g
    vy = uy - g * t
    add(
        "hard-kin-cliff",
        t=scalar(t, "s"),
        vx=directed(ux, "m/s", "+x"),
        vy=directed(vy, "m/s", "+y"),
        speed=scalar(s.sqrt(ux**2 + vy**2), "m/s"),
        range=scalar(ux * t, "m"),
    )

    theta, mu, mass = 28 * s.pi / 180, r("0.31"), r("1.7")
    a = -g * (s.sin(theta) + mu * s.cos(theta))
    d = -(r("6.4") ** 2) / (2 * a)
    add(
        "hard-energy-incline-up",
        a=directed(a, "m/s**2", "up the slope"),
        d=scalar(d, "m"),
        W_friction=scalar(-mu * mass * g * s.cos(theta) * d, "J"),
    )
    mass, mu, compression = r("0.85"), r("0.22"), r("0.12")
    energy = 420 * compression**2 / 2
    kinetic = energy - mu * mass * g * compression
    add(
        "hard-energy-spring-friction",
        U_spring=scalar(energy, "J"),
        v=scalar(s.sqrt(2 * kinetic / mass), "m/s"),
        s=scalar(kinetic / (mu * mass * g), "m"),
        W_friction=scalar(-energy, "J"),
    )
    work = 320 * r("17.2") ** 2 / 2 - 320 * g * r("18.5")
    add("hard-energy-coaster", W_friction=scalar(work, "J"), f=scalar(-work / 46, "N"))
    a = g * (r("1.6") - r("0.18") * 3) / (3 + r("1.6"))
    add(
        "hard-energy-table-pulley",
        v=scalar(s.sqrt(2 * a * r("0.75")), "m/s"),
        a=scalar(a, "m/s**2"),
        T=scalar(r("1.6") * (g - a), "N"),
    )
    theta, mu = 35 * s.pi / 180, r("0.08")
    length = 12 / s.sin(theta)
    v2 = 2 * g * (12 - mu * s.cos(theta) * length)
    add(
        "hard-energy-skier",
        L=scalar(length, "m"),
        v=scalar(s.sqrt(v2), "m/s"),
        s=scalar(v2 / (2 * mu * g), "m"),
    )

    add(
        "hard-charges-zero-field",
        E_mid=directed(k * r("4.2e-6") / r("0.25") ** 2, "N/C", "+x"),
        x0=scalar(r("0.5") / (1 - s.sqrt(r("1.2") / 3)), "m"),
    )
    points = [
        (r("4e-9"), s.Matrix([r("0.3"), 0])),
        (r("-6e-9"), s.Matrix([0, r("0.4")])),
        (r("2.5e-9"), s.Matrix([r("-0.2"), r("-0.2")])),
    ]
    potential = sum(k * q / p.norm() for q, p in points)
    energy = sum(
        k * qi * qj / (pi - pj).norm()
        for i, (qi, pi) in enumerate(points)
        for qj, pj in points[i + 1 :]
    )
    add(
        "hard-charges-potential",
        V0=scalar(potential, "V"),
        U=scalar(energy, "J"),
        W=scalar(r("-1.5e-9") * potential, "J"),
    )
    f21 = -k * r("5e-9") * r("2e-9") / r("0.2") ** 2
    f23 = k * r("3e-9") * r("2e-9") / r("0.3") ** 2
    add(
        "hard-charges-line-force",
        F21=directed(f21, "N", "+x"),
        F23=directed(f23, "N", "+x"),
        F_net=directed(f21 + f23, "N", "+x"),
    )
    field, charge, mass = 250 / r("0.018"), r("-1.602e-19"), r("9.109e-31")
    add(
        "hard-charges-electron-plates",
        E=scalar(field, "N/C"),
        F=directed(charge * field, "N", "+y"),
        v=scalar(s.sqrt(-2 * charge * 250 / mass), "m/s"),
    )
    x = r("0.05")
    force = -k * r("2e-9") * r("1e-9") / x**2 + k * r("5e-9") * r("1e-9") / (r("0.3") - x) ** 2
    add(
        "hard-charges-equilibrium",
        x_eq=scalar(r("0.3") * s.sqrt(2) / (s.sqrt(2) + s.sqrt(5)), "m"),
        F=directed(force, "N", "+x"),
    )
    m1, m2, u1, u2 = r("1.4"), r("2.1"), r("3.2"), r("-1.7")
    v1 = ((m1 - m2) * u1 + 2 * m2 * u2) / (m1 + m2)
    v2 = (2 * m1 * u1 + (m2 - m1) * u2) / (m1 + m2)
    kinetic = (m1 * u1**2 + m2 * u2**2) / 2
    assert s.simplify((m1 * v1**2 + m2 * v2**2) / 2 - kinetic) == 0
    add(
        "hard-mech-elastic-collision",
        v1=directed(v1, "m/s", "+x"),
        v2=directed(v2, "m/s", "+x"),
        J2=directed(m2 * (v2 - u2), "N*s", "+x"),
        KE=scalar(kinetic, "J"),
    )
    return answers
