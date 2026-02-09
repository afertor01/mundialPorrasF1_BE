def get_podium_drivers(positions_list):
    """
    Extrae los pilotos en las posiciones 1, 2 y 3.
    Devuelve una lista [1º, 2º, 3º] o None en esa posición si falta.
    """
    # Creamos un mapa {posicion: driver_name}
    pos_map = {p.position: p.driver_name for p in positions_list}
    
    # Retornamos [P1, P2, P3] usando .get() por si acaso falta alguno
    return [pos_map.get(1), pos_map.get(2), pos_map.get(3)]

def build_real_positions_map(race_positions):
    """
    Devuelve: {driver_name: position}
    """
    return {
        rp.driver_name: rp.position
        for rp in race_positions
    }

def calculate_base_points(prediction_positions, race_positions):
    real_map = build_real_positions_map(race_positions)
    total = 0

    for pp in prediction_positions:
        real_pos = real_map.get(pp.driver_name)
        if not real_pos:
            continue

        diff = abs(pp.position - real_pos)

        if diff == 0:
            total += 3
        elif diff == 1:
            total += 1

    return total

def build_event_map(events):
    """
    Devuelve: {event_type: value}
    """
    return {
        e.event_type: e.value
        for e in events
    }

def get_correct_events(prediction_events, race_events):
    """
    Compara los eventos predichos con los reales.
    Maneja lógica especial para DNF_DRIVER (lista de valores).
    """
    real_events = build_event_map(race_events)
    correct = []

    for pe in prediction_events:
        # Verificamos si el tipo de evento existe en los resultados reales
        if pe.event_type in real_events:
            real_val = str(real_events[pe.event_type])
            pred_val = str(pe.value)

            # --- CAMBIO IMPORTANTE AQUÍ ---
            if pe.event_type == "DNF_DRIVER":
                # La realidad es una lista "SAI, VER, HAM" y la predicción es "SAI"
                # Convertimos la lista real en un set para buscar fácil
                real_dnf_list = [x.strip() for x in real_val.split(",")]
                
                if pred_val in real_dnf_list:
                    correct.append(pe.event_type)
            
            # --- LÓGICA ESTÁNDAR PARA EL RESTO ---
            elif pred_val == real_val:
                correct.append(pe.event_type)

    return correct

def calculate_multiplier(correct_events, multiplier_configs):
    multiplier = 1.0

    for mc in multiplier_configs:
        if mc.event_type in correct_events:
            multiplier *= mc.multiplier

    return multiplier

def evaluate_podium(prediction_positions, race_positions):
    pred_podium = get_podium_drivers(prediction_positions)
    real_podium = get_podium_drivers(race_positions)

    if None in pred_podium or None in real_podium:
        return {
            "PODIUM_PARTIAL": False,
            "PODIUM_TOTAL": False
        }

    partial = set(pred_podium) == set(real_podium)
    total = pred_podium == real_podium

    return {
        "PODIUM_PARTIAL": partial,
        "PODIUM_TOTAL": total
    }


def calculate_prediction_score(
    prediction,
    race_result,
    multiplier_configs
):
    base_points = calculate_base_points(
        prediction.positions,
        race_result.positions
    )

    # Eventos declarativos
    correct_events = get_correct_events(
        prediction.events,
        race_result.events
    )

    # Eventos automáticos (podio)
    podium_result = evaluate_podium(
        prediction.positions,
        race_result.positions
    )

    if podium_result["PODIUM_TOTAL"]:
        correct_events.append("PODIUM_TOTAL")
    elif podium_result["PODIUM_PARTIAL"]:
        correct_events.append("PODIUM_PARTIAL")

    multiplier = calculate_multiplier(
        correct_events,
        multiplier_configs
    )

    final_points = int(base_points * multiplier)

    return {
        "base_points": base_points,
        "multiplier": multiplier,
        "final_points": final_points,
        "correct_events": correct_events
    }
