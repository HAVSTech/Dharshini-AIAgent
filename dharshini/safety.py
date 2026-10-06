from dataclasses import dataclass
@dataclass(frozen=True)
class Approval:
    allowed:bool
    reason:str=""
class SafetyManager:
    def __init__(self,require_confirmation=True):self.require_confirmation=require_confirmation
    def check(self,risk,confirm_callback=None):
        if risk=="SAFE":return Approval(True)
        if risk=="BLOCKED":return Approval(False,"Blocked by Dharshini safety policy.")
        if not self.require_confirmation:return Approval(True)
        if confirm_callback is None:return Approval(False,"User confirmation is required.")
        return Approval(bool(confirm_callback()),"User denied confirmation.")
