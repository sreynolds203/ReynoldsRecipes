"""
Ingredient parser for smart quantity aggregation in shopping lists.
Handles common fractions, units, and ingredient name normalization.
"""
import re
from fractions import Fraction
from typing import Dict, Tuple, Optional


# Map variant units to canonical units
UNIT_MAP = {
    # Volume
    'tsp': 'tsp',
    'teaspoon': 'tsp',
    'tbsp': 'tbsp',
    'tablespoon': 'tbsp',
    'cup': 'cup',
    'cups': 'cup',
    'ml': 'ml',
    'milliliter': 'ml',
    'l': 'l',
    'liter': 'l',
    'oz': 'oz',
    'ounce': 'oz',
    'pt': 'pt',
    'pint': 'pt',
    
    # Weight
    'g': 'g',
    'gram': 'g',
    'kg': 'kg',
    'kilogram': 'kg',
    'lb': 'lb',
    'lbs': 'lb',
    'pound': 'lb',
    
    # Count/other
    'pc': 'pc',
    'piece': 'pc',
    'clove': 'clove',
    'cloves': 'clove',
    'bunch': 'bunch',
    'can': 'can',
    'jar': 'jar',
    'package': 'package',
    'pkg': 'package',
}

# Conversion factors to a base unit (ml for volume, g for weight)
CONVERSIONS = {
    'tsp': 5,          # 1 tsp = 5 ml
    'tbsp': 15,        # 1 tbsp = 15 ml
    'cup': 240,        # 1 cup = 240 ml
    'ml': 1,
    'l': 1000,
    'oz': 30,          # 1 oz ≈ 30 ml (approximate for cooking)
    'pt': 473,         # 1 pint ≈ 473 ml
}


def parse_quantity(quantity_str: str) -> Optional[float]:
    """
    Parse a quantity string into a float value.
    Handles whole numbers, decimals, and fractions (e.g., '1/2', '1 1/2').
    
    Returns the quantity as a float, or None if parsing fails.
    """
    if not quantity_str or not quantity_str.strip():
        return None
    
    quantity_str = quantity_str.strip()
    
    # Handle mixed fractions like "1 1/2"
    match = re.match(r'^(\d+)\s+(\d+)/(\d+)$', quantity_str)
    if match:
        whole = int(match.group(1))
        numerator = int(match.group(2))
        denominator = int(match.group(3))
        return whole + (numerator / denominator)
    
    # Handle simple fractions like "1/2"
    match = re.match(r'^(\d+)/(\d+)$', quantity_str)
    if match:
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        return numerator / denominator
    
    # Handle decimals and whole numbers
    try:
        return float(quantity_str)
    except ValueError:
        return None


def normalize_ingredient(ingredient_line: str) -> Tuple[Optional[float], Optional[str], str]:
    """
    Parse an ingredient line into (quantity, unit, ingredient_name).
    
    Examples:
        "2 cups flour" -> (2.0, "cup", "flour")
        "1/2 tsp salt" -> (0.5, "tsp", "salt")
        "3 cloves garlic" -> (3.0, "clove", "garlic")
        "flour" -> (None, None, "flour")
        "to taste" -> (None, None, "to taste")
    
    Returns: (quantity, canonical_unit, ingredient_name)
    """
    ingredient_line = ingredient_line.strip()
    if not ingredient_line:
        return None, None, ""
    
    # Pattern: optional quantity + optional unit + rest is ingredient name
    # Quantity can be: "1", "1.5", "1/2", "1 1/2"
    pattern = r'^([0-9./\s]+)?\s*([a-z]{1,}(?:\s+[a-z]+)?)?\s*(.+)$'
    match = re.match(pattern, ingredient_line, re.IGNORECASE)
    
    if not match:
        return None, None, ingredient_line
    
    quantity_str, unit_str, ingredient_name = match.groups()
    
    # Parse quantity
    quantity = None
    if quantity_str:
        quantity = parse_quantity(quantity_str.strip())
    
    # Normalize unit
    unit = None
    if unit_str:
        unit_lower = unit_str.strip().lower()
        unit = UNIT_MAP.get(unit_lower, unit_lower)
    
    # Clean ingredient name
    ingredient_name = ingredient_name.strip().lower() if ingredient_name else ""
    
    return quantity, unit, ingredient_name


def aggregate_ingredients(ingredients: Dict[str, Tuple[float, str]]) -> Dict[str, Tuple[float, str]]:
    """
    Merge ingredients with the same name but potentially different units/quantities.
    
    For ingredients without a common convertible unit (e.g., "2 cups flour" + "3 tbsp flour"),
    we'll keep them separate if they have different units.
    
    Returns a dict mapping ingredient_name -> (total_quantity, unit)
    """
    aggregated = {}
    
    for ing_name, (qty, unit) in ingredients.items():
        if ing_name not in aggregated:
            aggregated[ing_name] = (qty, unit)
        else:
            existing_qty, existing_unit = aggregated[ing_name]
            
            # If both have the same unit, just add quantities
            if unit == existing_unit:
                new_qty = (existing_qty or 0) + (qty or 0)
                aggregated[ing_name] = (new_qty, unit)
            else:
                # Different units: try to convert if both are in CONVERSIONS
                if unit in CONVERSIONS and existing_unit in CONVERSIONS:
                    # Convert everything to the first unit we encountered
                    existing_in_base = (existing_qty or 0) * CONVERSIONS[existing_unit]
                    current_in_base = (qty or 0) * CONVERSIONS[unit]
                    total_in_base = existing_in_base + current_in_base
                    total_qty = total_in_base / CONVERSIONS[existing_unit]
                    aggregated[ing_name] = (total_qty, existing_unit)
                else:
                    # Can't convert; create a separate entry with a combined label
                    # For now, we'll just keep the original and add a note
                    key = f"{ing_name} ({existing_unit})" if existing_unit else ing_name
                    aggregated[key] = (existing_qty, existing_unit)
                    key2 = f"{ing_name} ({unit})" if unit else ing_name
                    aggregated[key2] = (qty, unit)
    
    return aggregated


def format_quantity(quantity: Optional[float], unit: Optional[str]) -> str:
    """
    Format a quantity and unit for display.
    Converts decimal quantities to fractions when appropriate.
    
    Examples:
        (2.0, "cup") -> "2 cups"
        (0.5, "tsp") -> "1/2 tsp"
        (1.5, "tbsp") -> "1 1/2 tbsp"
        (None, None) -> ""
    """
    if quantity is None:
        return unit or ""
    
    # Convert decimal to fraction for display
    frac = Fraction(quantity).limit_denominator(8)
    
    # Format quantity string
    if frac.denominator == 1:
        qty_str = str(frac.numerator)
    else:
        if frac.numerator > frac.denominator:
            whole = frac.numerator // frac.denominator
            remainder = frac.numerator % frac.denominator
            if remainder:
                qty_str = f"{whole} {remainder}/{frac.denominator}"
            else:
                qty_str = str(whole)
        else:
            qty_str = f"{frac.numerator}/{frac.denominator}"
    
    # Pluralize unit if quantity > 1
    if unit and quantity > 1 and not unit.endswith('s'):
        unit_display = unit + 's'
    else:
        unit_display = unit or ""
    
    return f"{qty_str} {unit_display}".strip()
