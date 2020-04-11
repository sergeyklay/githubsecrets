import click
import requests
import json
from base64 import b64encode
from nacl import encoding, public

# Reference: https://developer.github.com/v3/actions/secrets/


class Secret():
    @staticmethod
    def encrypt(public_key: str, secret_value: str) -> str:
        """
        Encrypts a Unicode string using the public key, returns base64 of the publickey
        """  # noqa: E501
        public_key = public.PublicKey(
            public_key.encode("utf-8"), encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return b64encode(encrypted).decode("utf-8")

    @staticmethod
    def print_response(response):
        """Prints a human-readable response"""
        res = {}
        if (response.text):
            try:
                res['body'] = response.json()
            except:  # noqa: E722
                res['body'] = response.text
        res['status_code'] = response.status_code
        click.echo(json.dumps(res, indent=4, sort_keys=True))

    def request(self, method, api_path, parameters={}) -> requests.request:
        full_url = f"{self.base_url}/{api_path}"
        headers = {
            'Authorization': f"token {self.profile.personal_access_token}"}
        return requests.request(
            method,
            url=full_url,
            headers=headers,
            json=parameters
        )

    def get_public_key(self) -> requests.request:
        """Get the repository's public key, used when creating/updating a secret"""  # noqa: E501
        self.public_key = self.request('get', 'actions/secrets/public-key')

    def __init__(self, profile, repository, name='', value=''):
        self.profile = profile
        if not profile.github_owner:
            click.echo(f"""FAILED: Profile doesn't exist - {self.profile.name}
Fix with: ghs profile-apply -p {self.profile.name}
            """)
            exit()
        self.repository = repository
        self.name = name.strip()
        self.value = value.strip()
        self.base_url = "/".join([
            "https://api.github.com/repos",
            self.profile.github_owner,
            self.repository
        ])

    def apply(self):
        """Create or update a secret"""

        if not self.name or not self.value:
            click.echo("FAILED: Missing name or value")

        if self.profile.github_owner and self.profile.personal_access_token:
            self.get_public_key()
            if not 200 <= self.public_key.status_code < 300:
                raise Exception(self.public_key.text)
            else:
                public_key = self.public_key.json()

            encrypted_value = Secret.encrypt(
                public_key['key'], self.value)

            parameters = {
                "encrypted_value": encrypted_value,
                "key_id": public_key['key_id']
            }

            response = self.request(
                'put',
                f"actions/secrets/{self.name}",
                parameters=parameters
            )

            Secret.print_response(response)

        else:
            click.echo(f"FAILED: Unable to fetch profile {self.profile_name}")

    def lista(self):
        """Lists all secrets in repository"""
        response = self.request('get', "actions/secrets")
        Secret.print_response(response)

    def delete(self):
        """Delete a secret"""
        response = self.request('delete', f"actions/secrets/{self.name}")
        Secret.print_response(response)

    def get(self):
        """Get a secret"""
        response = self.request('get', f"actions/secrets/{self.name}")
        Secret.print_response(response)