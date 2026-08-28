from problem.models import RemoteOJ

from .models import RemoteSubmissionStatus, Submission
from utils.api import serializers
from utils.serializers import LanguageNameChoiceField


class CreateSubmissionSerializer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    language = LanguageNameChoiceField()
    code = serializers.CharField(max_length=1024 * 1024)
    contest_id = serializers.IntegerField(required=False)
    captcha = serializers.CharField(required=False)


class ShareSubmissionSerializer(serializers.Serializer):
    id = serializers.CharField()
    shared = serializers.BooleanField()


class RemoteSubmissionEventSerializer(serializers.Serializer):
    submission_id = serializers.CharField(max_length=64)
    provider = serializers.ChoiceField(choices=RemoteOJ.choices())
    status = serializers.ChoiceField(choices=[
        RemoteSubmissionStatus.QUEUED,
        RemoteSubmissionStatus.OPENING,
        RemoteSubmissionStatus.AUTH_REQUIRED,
        RemoteSubmissionStatus.VERIFICATION_REQUIRED,
        RemoteSubmissionStatus.SUBMITTED,
        RemoteSubmissionStatus.JUDGING,
        RemoteSubmissionStatus.FINISHED,
        RemoteSubmissionStatus.FAILED,
    ])
    remote_submission_id = serializers.CharField(max_length=128, allow_blank=True, required=False)
    remote_url = serializers.URLField(max_length=1024, allow_blank=True, required=False)
    verdict = serializers.CharField(max_length=128, allow_blank=True, required=False)
    message = serializers.CharField(max_length=2048, allow_blank=True, required=False)
    time_ms = serializers.IntegerField(min_value=0, required=False)
    memory_bytes = serializers.IntegerField(min_value=0, required=False)
    passed_tests = serializers.IntegerField(min_value=0, required=False)
    total_tests = serializers.IntegerField(min_value=0, required=False)
    score = serializers.FloatField(min_value=0, required=False)
    verification_source = serializers.CharField(max_length=64, allow_blank=True, required=False)


class SubmissionModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Submission
        fields = "__all__"


# 不显示submission info的serializer, 用于ACM rule_type
class SubmissionSafeModelSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")

    class Meta:
        model = Submission
        exclude = ("info", "contest", "ip")


class SubmissionListSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")
    show_link = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Submission
        exclude = ("info", "contest", "code", "ip")

    def get_show_link(self, obj):
        # 没传user或为匿名user
        if self.user is None or not self.user.is_authenticated:
            return False
        return obj.check_user_permission(self.user)
