def _all_text(data):
    players = data.get("players", [])
    parts = [
        str(data.get("formation", "")),
        str(data.get("playstyle", "")),
    ]
    for p in players:
        parts.extend([
            str(p.get("name", "")),
            str(p.get("position", "")),
            str(p.get("playstyle", "")),
        ])
    return " ".join(parts).lower()


def analyze_squad_data(data, from_vision=False):
    formation = data.get("formation", "Unknown")
    playstyle = data.get("playstyle", "Unknown")
    players = data.get("players", []) or []
    notes = data.get("notes", []) or []

    text = _all_text(data)

    score = 70
    issues = []
    fixes = []

    if "anchor man" in text:
        score += 8
    else:
        issues.append("No Anchor Man was identified.")
        fixes.append("Consider an Anchor Man DMF when you need stronger central protection.")

    if "build up" in text:
        score += 7
    else:
        issues.append("No Build Up CB was identified.")
        fixes.append("Consider a Build Up CB for safer first-phase progression.")

    if "goal poacher" in text or "fox in the box" in text:
        score += 6
    else:
        issues.append("No obvious penalty-box finisher was identified.")
        fixes.append("Consider a Goal Poacher or Fox in the Box for central finishing.")

    if "defensive fullback" in text:
        score += 3

    if "possession" in text and "offensive fullback" not in text:
        fixes.append("An attacking fullback could add width if midfield cover is sufficient.")

    if "quick counter" in text:
        fixes.append("Prioritize pace, direct passing and runners behind the defensive line.")

    if len(players) >= 8:
        score += 6
    elif from_vision:
        issues.append("The screenshot did not provide enough clearly readable player data.")
        fixes.append("Send a higher-resolution screenshot with the full squad visible.")

    score = max(0, min(100, score))

    lines = [
        "⚽ *eFOOTBALL AI SQUAD DOCTOR V2*",
        "",
        f"📐 Formation: *{formation}*",
        f"🎮 Playstyle: *{playstyle}*",
        f"👥 Players recognized: *{len(players)}*",
        f"⭐ Structural score: *{score}/100*",
        "",
        "🔴 *Potential issues*",
    ]

    if issues:
        lines.extend("• " + x for x in issues)
    else:
        lines.append("• No major structural issue detected from the supplied data.")

    lines.extend(["", "🔧 *Recommendations*"])
    if fixes:
        lines.extend("• " + x for x in fixes)
    else:
        lines.append("• Squad structure looks balanced from the supplied data.")

    if players:
        lines.extend(["", "👤 *Recognized players*"])
        for p in players[:18]:
            name = p.get("name", "Unknown")
            pos = p.get("position", "Unknown")
            style = p.get("playstyle", "Unknown")
            if style and style.lower() != "unknown":
                lines.append(f"• {name} — {pos} — {style}")
            else:
                lines.append(f"• {name} — {pos}")

    if notes:
        lines.extend(["", "ℹ️ *Vision notes*"])
        for n in notes[:4]:
            lines.append("• " + str(n))

    lines.extend([
        "",
        "ℹ️ Tactical score is a heuristic, not an official Konami rating."
    ])

    return "\n".join(lines)
