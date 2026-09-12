"""
Duplicate Detector

Uses exact and fuzzy matching to prevent importing duplicate leads.
"""

from Levenshtein import ratio
import tldextract


class DuplicateDetector:
    """Detects duplicate leads using fuzzy logic."""
    
    @staticmethod
    def normalize_domain(url: str | None) -> str | None:
        if not url:
            return None
        ext = tldextract.extract(url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}".lower()
        return None
        
    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        if not phone:
            return None
        return "".join(filter(str.isdigit, phone))
        
    def is_duplicate(self, existing_lead: dict, new_lead_data: dict) -> bool:
        """
        Check if new_lead_data is a duplicate of existing_lead.
        existing_lead should be a dictionary representation of the Lead model.
        """
        # 1. Exact Domain Match
        existing_domain = self.normalize_domain(existing_lead.get("domain") or existing_lead.get("website"))
        new_domain = self.normalize_domain(new_lead_data.get("domain") or new_lead_data.get("website"))
        
        if existing_domain and new_domain and existing_domain == new_domain:
            return True
            
        # 2. Exact Phone Match
        existing_phone = self.normalize_phone(existing_lead.get("phone"))
        new_phone = self.normalize_phone(new_lead_data.get("phone"))
        
        if existing_phone and new_phone and existing_phone == new_phone:
            return True
            
        # 3. Fuzzy Name Match + Same City
        existing_name = str(existing_lead.get("name") or "").lower().strip()
        new_name = str(new_lead_data.get("name") or "").lower().strip()
        
        existing_city = str(existing_lead.get("city") or "").lower().strip()
        new_city = str(new_lead_data.get("city") or "").lower().strip()
        
        if existing_name and new_name and existing_city and new_city:
            if existing_city == new_city:
                similarity = ratio(existing_name, new_name)
                if similarity > 0.85:
                    return True
                    
        return False
