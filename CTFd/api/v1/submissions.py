from flask import request
from flask_restx import Namespace, Resource

from CTFd.cache import clear_standings
from CTFd.models import Submissions, db
from CTFd.schemas.submissions import SubmissionSchema
from CTFd.utils.decorators import admins_only

submissions_namespace = Namespace(
    "submissions", description="Endpoint to retrieve Submission"
)


@submissions_namespace.route("")
class SubmissionsList(Resource):
    @admins_only
    def get(self):
        args = request.args.to_dict()
        schema = SubmissionSchema(many=True)
        pagination_args = {
            "per_page": int(args.pop("per_page", 50)),
            "page": int(args.pop("page", 1)),
        }
        if args:
            submissions = Submissions.query.filter_by(**args).paginate(
                **pagination_args, max_per_page=100
            )
        else:
            submissions = Submissions.query.paginate(
                **pagination_args, max_per_page=100
            )

        response = schema.dump(submissions.items)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {
            "meta": {
                "pagination": {
                    "page": submissions.page,
                    "next": submissions.next_num,
                    "prev": submissions.prev_num,
                    "pages": submissions.pages,
                    "per_page": submissions.per_page,
                    "total": submissions.total,
                }
            },
            "success": True,
            "data": response.data,
        }

    @admins_only
    def post(self):
        req = request.get_json()
        Model = Submissions.get_child(type=req.get("type"))
        schema = SubmissionSchema(instance=Model())
        response = schema.load(req)
        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        db.session.add(response.data)
        db.session.commit()

        response = schema.dump(response.data)
        db.session.close()

        # Delete standings cache
        clear_standings()

        return {"success": True, "data": response.data}


@submissions_namespace.route("/<submission_id>")
@submissions_namespace.param("submission_id", "A Submission ID")
class Submission(Resource):
    @admins_only
    def get(self, submission_id):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        schema = SubmissionSchema()
        response = schema.dump(submission)

        if response.errors:
            return {"success": False, "errors": response.errors}, 400

        return {"success": True, "data": response.data}

    @admins_only
    def delete(self, submission_id):
        submission = Submissions.query.filter_by(id=submission_id).first_or_404()
        db.session.delete(submission)
        db.session.commit()
        db.session.close()

        # Delete standings cache
        clear_standings()

        return {"success": True}
