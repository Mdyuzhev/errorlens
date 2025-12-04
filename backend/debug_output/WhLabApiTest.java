package com.errorlens.tests;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import org.junit.jupiter.api.*;
import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Auto-generated REST Assured tests from ErrorLens session.
 * Base URL: https://api.wh-lab.ru
 *
 * Tests run in order using @TestMethodOrder annotation.
 * Authentication token is shared between tests.
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class WhLabApiTest {

    // Shared auth token extracted from login response
    private static String authToken;

    @BeforeAll
    public static void setup() {
        RestAssured.baseURI = "https://api.wh-lab.ru";
    }

    @Order(1)
    @Test
    @DisplayName("POST /api/auth/login")
    public void test01_postAuthLogin() {
        Response response = given()
            .header("Content-Type", "application/json")
            .contentType("application/json")
            .body("{\"username\": \"ivanov\", \"password\": \"password123\"}")
        .when()
            .post("/api/auth/login")
        .then()
            .statusCode(200)
            .extract().response();

        // Extract auth token from response
        authToken = response.jsonPath().getString("token");
        if (authToken == null) {
            authToken = response.jsonPath().getString("access_token");
        }
        assertNotNull(authToken, "Auth token not found in login response");
    }

    @Order(2)
    @Test
    @DisplayName("GET /api/products")
    public void test02_getApiProducts() {
        given()
            .header("Authorization", "Bearer " + authToken)
        .when()
            .get("/api/products")
        .then()
            .statusCode(200)
            .log().ifError();
    }

    @Order(3)
    @Test
    @DisplayName("POST /api/products")
    public void test03_postApiProducts() {
        given()
            .header("Authorization", "Bearer " + authToken)
            .header("Content-Type", "application/json")
            .contentType("application/json")
            .body("{\"name\": \"Тест\", \"quantity\": 1, \"price\": 12, \"description\": \"Тест\", \"category\": \"Одежда\"}")
        .when()
            .post("/api/products")
        .then()
            .statusCode(201)
            .body("id", notNullValue())
            .body("name", notNullValue())
            .body("quantity", notNullValue())
            .log().ifError();
    }

    @Order(4)
    @Test
    @DisplayName("GET /api/products")
    public void test04_getApiProducts() {
        given()
            .header("Authorization", "Bearer " + authToken)
        .when()
            .get("/api/products")
        .then()
            .statusCode(200)
            .log().ifError();
    }

}
