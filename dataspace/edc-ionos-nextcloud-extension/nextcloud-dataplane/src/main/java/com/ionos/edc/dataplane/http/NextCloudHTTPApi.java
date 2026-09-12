package com.ionos.edc.dataplane.http;


import com.ionos.edc.http.HttpParts;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import org.eclipse.edc.web.spi.ApiErrorDetail;
import org.springframework.http.ResponseEntity;

public interface NextCloudHTTPApi {

    @Operation(description = "Start transfer between provider and consumer. ",
            responses = {
                    @ApiResponse(responseCode = "200"),
                    @ApiResponse(responseCode = "400", description = "Request was malformed, e.g. id was null",
                            content = @Content(array = @ArraySchema(schema = @Schema(implementation = ApiErrorDetail.class))))
            })
    ResponseEntity<String> startTransferProcess (HttpParts httpParts);
}
