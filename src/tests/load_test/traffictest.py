import random
import string

from locust import HttpUser, task


def random_string(length: int = 10) -> str:
    return "".join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )


class User(HttpUser):
    token = None

    def on_start(self) -> None:
        """Create a user and login when a virtual user starts."""
        self.email = f"loadtest_{random_string(8)}@example.com"
        self.password = "Secr3tP@ssword!"

        self.client.post(
            "/api/v1/accounts/register/",
            json={
                "email": self.email,
                "password": self.password
            },
            name="Register User",
        )

        # Temporarily changed default value for UserModel.is_active from False to True

        response = self.client.post(
            "/api/v1/accounts/login/",
            json={"email": self.email, "password": self.password},
            name="Login User",
        )

        if response.status_code == 200:
            self.token = response.json().get("access_token")

    def get_auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(1)
    def swagger_docs(self) -> None:
        self.client.get("/docs", name="Swagger Documentation")

    @task(1)
    def redoc_docs(self) -> None:
        self.client.get("/redoc", name="ReDoc Documentation")

    @task(20)
    def browse_movies(self) -> None:
        """Users frequently browse the movie catalog."""
        page = random.randint(1, 10)
        self.client.get(
            f"/api/v1/cinema/movies/?page={page}&per_page=10",
            name="Browse Movies",
        )

    @task(15)
    def view_movie_details(self) -> None:
        """Users frequently click on a specific movie to see details."""
        movie_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/cinema/movies/{movie_id}/", name="View Movie Details"
        )

    @task(10)
    def search_movies(self) -> None:
        """Users search for movies by name or genre."""
        search_terms = ["action", "drama", "comedy", "matrix", "godfather"]
        term = random.choice(search_terms)
        self.client.get(
            f"/api/v1/cinema/movies/?search={term}", name="Search Movies"
        )

    @task(5)
    def browse_genres(self) -> None:
        """Users browse available genres."""
        self.client.get(
            "/api/v1/cinema/genres/",
            headers=self.get_auth_headers(),
            name="Browse Genres"
        )

    @task(5)
    def browse_directors(self) -> None:
        """Users browse available directors."""
        self.client.get(
            "/api/v1/cinema/directors/",
            headers=self.get_auth_headers(),
            name="Browse Directors"
        )

    @task(5)
    def browse_stars(self) -> None:
        """Users browse available stars/actors."""
        self.client.get(
            "/api/v1/cinema/stars/",
            headers=self.get_auth_headers(),
            name="Browse Stars"
        )

    @task(3)
    def view_cart(self) -> None:
        """Authenticated users occasionally view their shopping cart."""
        if self.token:
            self.client.get(
                "/api/v1/ecommerce/cart/",
                headers=self.get_auth_headers(),
                name="View Shopping Cart",
            )
