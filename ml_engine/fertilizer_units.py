def convert_to_kg(quantity , unit):
    """"" convert a known fertilizer quantity to kilograms"""

    try:
        quantity = float(quantity)
    except(TypeError ,  ValueError):
        return None,"invalid_quantity"

    if quantity < 0:
        return None,"invalid_quantity"
    unit = str(unit).strip().lower()

    if unit == "kg":
                    return quantity , "converted"

    if unit == "quintal":
                    return quantity*100 , "converted"
    return None, "unknown_unit"


if __name__ == "__main__":
        examples =[
                (50 , "Kg"),
                (1,"Quintal"),
                (3,"Bag"),
        ]

        for quantity, unit in examples:
            result , status = convert_to_kg(quantity,unit)
            print(f"{quantity} {unit} -> {result} kg | {status}")