import uuid
import hashlib
from typing import List, Dict
from itertools import groupby

from src.models import ExtractedField, CanonicalProfile, ProvenanceRecord, Skill
from src.normalizers.normalizer import DataNormalizer
from src.confidence.calculator import ConfidenceCalculator
import phonenumbers

class MergeEngine:
    """
    Master Data Management Engine
    Implements advanced conflict resolution strategies: Field-priority, Recency, Specificity, Validation, and Voting.
    """
    
    # 1. Field-Aware Source Priority
    FIELD_PRIORITY = {
        "full_name": ["resume_pdf", "csv"],
        "emails": ["csv", "resume_pdf"],
        "phones": ["csv", "resume_pdf"],
        "location": ["resume_pdf", "csv"],
        "headline": ["resume_pdf", "csv"],
        "experience": ["resume_pdf", "csv"],
        "education": ["resume_pdf", "csv"],
        "skills": ["resume_pdf", "csv"]
    }
    
    ARRAY_FIELDS = {"emails", "phones", "experience", "education"} # Skills handled separately by Voting

    def _generate_deterministic_id(self, fields: List[ExtractedField]) -> str:
        """Generates a stable UUID-like string based on core identifier fields."""
        emails = [f.value for f in fields if f.field == "emails" and f.value]
        if emails:
            # Hash the first alphabetically sorted normalized email for stability
            seed_str = f"email:{sorted(emails)[0]}"
        else:
            names = [f.value for f in fields if f.field == "full_name" and f.value]
            phones = [f.value for f in fields if f.field == "phones" and f.value]
            seed_str = f"name:{sorted(names)[0] if names else 'unknown'}_phone:{sorted(phones)[0] if phones else 'unknown'}"
            
        md5 = hashlib.md5(seed_str.encode('utf-8')).hexdigest()
        # Format as UUID
        return f"{md5[:8]}-{md5[8:12]}-{md5[12:16]}-{md5[16:20]}-{md5[20:]}"

    def merge(self, fields: List[ExtractedField]) -> CanonicalProfile:
        # Pre-normalize for ID generation and merging
        for c in fields:
            c.value = DataNormalizer.normalize(c.field, c.value)
            
        candidate_id = self._generate_deterministic_id(fields)
        profile = CanonicalProfile(candidate_id=candidate_id, full_name="")
        
        fields.sort(key=lambda x: x.field)
        
        for field_name, group in groupby(fields, key=lambda x: x.field):
            candidates = list(group)
            
            # Normalize first
            for c in candidates:
                c.value = DataNormalizer.normalize(c.field, c.value)
            
            candidates = [c for c in candidates if c.value is not None]
            if not candidates:
                continue

            if field_name == "skills":
                self._merge_skills_vote(profile, candidates)
            elif field_name in self.ARRAY_FIELDS:
                self._merge_array_field(profile, field_name, candidates)
            else:
                self._merge_single_field(profile, field_name, candidates)
                
        profile.overall_confidence = ConfidenceCalculator.calculate_overall(profile.field_confidence)
        return profile

    def _score_candidate(self, field_name: str, candidate: ExtractedField) -> tuple:
        """
        Creates a scoring tuple for sorting. Python sorts tuples element by element.
        Tuple: (Priority Score, Recency, Specificity, Structural Validation)
        Higher is better, so we negate priority (lower priority index = better).
        """
        priorities = self.FIELD_PRIORITY.get(field_name, [])
        priority_score = -priorities.index(candidate.source) if candidate.source in priorities else -99
        
        # Structural Validation: Does it look perfectly formed?
        validation_score = 0
        if field_name == "phones" and isinstance(candidate.value, str) and candidate.value.startswith("+"):
            validation_score = 1 # Perfect E.164
        elif field_name == "emails" and isinstance(candidate.value, str) and "@" in candidate.value and "." in candidate.value:
            validation_score = 1 # Looks like a real email
            
        return (validation_score, priority_score, candidate.timestamp, candidate.specificity_score)

    def _merge_single_field(self, profile: CanonicalProfile, field_name: str, candidates: List[ExtractedField]):
        # Sort using our advanced scoring tuple (reverse=True because higher tuple is better)
        candidates.sort(key=lambda c: self._score_candidate(field_name, c), reverse=True)
        winner = candidates[0]
        losers = candidates[1:]
        
        setattr(profile, field_name, winner.value)
        self._record_metadata(profile, field_name, winner, candidates, method="field_priority_winner")
        
        for loser in losers:
             prov = ProvenanceRecord(
                field=field_name, source=loser.source, raw_value=loser.raw_value,
                normalized_value=loser.value, method="ignored_lower_priority"
             )
             profile.provenance.append(prov)


    def _merge_array_field(self, profile: CanonicalProfile, field_name: str, candidates: List[ExtractedField]):
        winning_values = []
        # Sort arrays so higher priority/better sources appear first
        candidates.sort(key=lambda c: self._score_candidate(field_name, c), reverse=True)
        
        for c in candidates:
            vals = c.value if isinstance(c.value, list) else [c.value]
            for v in vals:
                if v not in winning_values:
                    winning_values.append(v)
                    prov = ProvenanceRecord(
                        field=field_name, source=c.source, raw_value=c.raw_value,
                        normalized_value=v, method="union_dedup"
                    )
                    profile.provenance.append(prov)
        
        setattr(profile, field_name, winning_values)
        if winning_values:
            base_confs = [ConfidenceCalculator.SOURCE_RELIABILITY.get(c.source, 0.5) for c in candidates]
            profile.field_confidence[field_name] = round(sum(base_confs) / len(base_confs), 2)

    def _merge_skills_vote(self, profile: CanonicalProfile, candidates: List[ExtractedField]):
        """Vote-based for arrays: Skills need high trust or multiple sources to get high confidence."""
        skill_map = {} # name -> list of sources
        
        for c in candidates:
            vals = c.value if isinstance(c.value, list) else [c.value]
            for v in vals:
                if v not in skill_map:
                    skill_map[v] = []
                skill_map[v].append(c.source)
                
        final_skills = []
        for skill_name, sources in skill_map.items():
            sources = list(set(sources)) # Unique sources
            # Rule: If it's in 2+ sources OR from a highly trusted source (resume), confidence is high.
            if len(sources) >= 2 or "resume_pdf" in sources:
                conf = 0.95
            else:
                conf = 0.50 # Single untrusted source
                
            final_skills.append(Skill(name=skill_name, confidence=conf, sources=sources))
            
            # Add to provenance
            prov = ProvenanceRecord(
                field="skills", source="both" if len(sources)>1 else sources[0], 
                raw_value=skill_name, normalized_value=skill_name, method="corroboration_vote"
            )
            profile.provenance.append(prov)
            
        profile.skills = final_skills
        avg_conf = sum(s.confidence for s in final_skills) / len(final_skills) if final_skills else 0.0
        profile.field_confidence["skills"] = round(avg_conf, 2)

    def _record_metadata(self, profile: CanonicalProfile, field_name: str, winner: ExtractedField, all_candidates: List[ExtractedField], method: str):
        prov = ProvenanceRecord(
            field=field_name, source=winner.source, raw_value=winner.raw_value,
            normalized_value=winner.value, method=method
        )
        profile.provenance.append(prov)
        conf = ConfidenceCalculator.calculate_field_confidence(winner, all_candidates)
        profile.field_confidence[field_name] = round(conf, 2)
