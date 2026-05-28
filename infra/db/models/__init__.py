# SQLAlchemy Models
#
# One file per domain. Not one giant models.py.
#
# Files (all to be created):
#   - session.py: SessionRecord, MessageRecord, ThreadRecord (Layer 1)
#   - memory.py: EpisodicRecord, SemanticRecord, IdentityRecord, ConsolidationRunRecord (Layer 2)
#   - persona.py: PersonalityVectorRecord, EntityBeliefRecord (Layer 4)
#   - relationship.py: RelationshipRecord, SocialGraphNode, DisclosureLogEntry, MilestoneRecord (Layer 5)
#   - proactivity.py: PatternObject, NotificationRecord, IntrusionThresholdRecord (Layer 6)
#   - goals.py: GoalRecord, TaskStepRecord, ConflictRecord, LifeEventRecord (Layer 7)
#   - tools.py: ActionRecord, PendingConfirmation (Layer 8)
#   - output_prefs.py: UserFormatProfile, VoicePreference (Layer 9)
#   - longitudinal.py: WeeklySummaryRecord, NarrativeChapterRecord, TurningPointRecord, ProgressDimensionRecord (Layer 10)
#   - safety.py: SafetyRecord, DependencyScoreRecord, GuardrailViolationLog (Layer 11)
#   - privacy.py: DeletionCertificate, ConsentRecord, IntegrityCheckRecord, SyncDeltaRecord (Layer 12)
#   - onboarding.py: ColdStartRecord, ElicitationRecord, FeatureReadinessRecord (Layer 13)
