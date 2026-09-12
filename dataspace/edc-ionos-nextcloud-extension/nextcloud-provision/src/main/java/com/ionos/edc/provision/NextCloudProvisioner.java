package com.ionos.edc.provision;


import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ionos.edc.http.HttpParts;
import com.ionos.edc.nextcloudapi.NextCloudApi;
import com.ionos.edc.schema.NextcloudSchema;
import com.ionos.edc.token.NextCloudToken;
import dev.failsafe.RetryPolicy;

import org.eclipse.edc.connector.controlplane.services.spi.transferprocess.TransferProcessService;
import org.eclipse.edc.connector.controlplane.transfer.spi.provision.Provisioner;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.*;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.policy.model.Policy;
import org.eclipse.edc.spi.EdcException;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.response.ResponseStatus;
import org.eclipse.edc.spi.response.StatusResult;
import okhttp3.MediaType;
import okhttp3.Request;
import okhttp3.RequestBody;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

import static org.eclipse.edc.spi.constants.CoreConstants.EDC_NAMESPACE;
import static org.eclipse.edc.web.spi.exception.ServiceResultHandler.exceptionMapper;

public class NextCloudProvisioner  implements Provisioner<NextCloudResourceDefinition, NextCloudProvisionedResource> {
    private static final MediaType JSON = MediaType.get("application/json");
    private RetryPolicy<Object> retryPolicy;
    private Monitor monitor;
    private NextCloudApi nextCloudApi;
    private final EdcHttpClient httpClient;
    private final ObjectMapper mapper;
    private String authKey;
    private String endpoint = "/nextcloudtransfer";
    private final TransferProcessService transferProcessService;
    public NextCloudProvisioner(RetryPolicy<Object> retryPolicy, Monitor monitor, NextCloudApi nextCloudApi, EdcHttpClient httpClient, ObjectMapper mapper, String authKey, TransferProcessService transferProcessService) {
        this.retryPolicy = retryPolicy;
        this.monitor = monitor;
        this.nextCloudApi = nextCloudApi;
        this.httpClient = httpClient;
        this.mapper = mapper;
        this.authKey = authKey;
        this.transferProcessService = transferProcessService;

    }

    @Override
    public boolean canProvision(ResourceDefinition resourceDefinition) {
        return resourceDefinition instanceof NextCloudResourceDefinition;
    }

    @Override
    public boolean canDeprovision(ProvisionedResource resourceDefinition) {
        return resourceDefinition instanceof NextCloudProvisionedResource;
    }

    @Override
    public CompletableFuture<StatusResult<ProvisionResponse>> provision(NextCloudResourceDefinition resourceDefinition, Policy policy) {
        String fileNameDest = resourceDefinition.getDataRequest().getDataDestination().getStringProperty(NextcloudSchema.FILE_NAME);
        String filePathDest = resourceDefinition.getDataRequest().getDataDestination().getStringProperty(NextcloudSchema.FILE_PATH);
        String filePath = resourceDefinition.getDataAddress().getStringProperty(NextcloudSchema.FILE_PATH);
        String fileName = resourceDefinition.getDataAddress().getStringProperty(NextcloudSchema.FILE_NAME);

        String resourceName = resourceDefinition.getDataAddress().getKeyName();

        if( policy.getExtensibleProperties().isEmpty()){
            return CompletableFuture.completedFuture(StatusResult.failure(ResponseStatus.FATAL_ERROR, "Extensible properties is mandatory"));
        }

        if (Boolean.parseBoolean(  getProperties(policy,EDC_NAMESPACE+"downloadable"))) {

            var resourceBuilder = NextCloudProvisionedResource.Builder.newInstance()
                    .id(resourceDefinition.getId())
                    .resourceName(resourceName)
                    .filePath(filePathDest)
                    .fileName(fileNameDest)
                    .urlKey(filePathDest + fileNameDest + resourceDefinition.getId())
                    .resourceDefinitionId(resourceDefinition.getId())
                    .transferProcessId(resourceDefinition.getDataRequest().getId())
                    .hasToken(true);

            var resource = resourceBuilder.build();
            try {
                var urlKey = "";
                if (resourceDefinition.getDataAddress().getType().equals(NextcloudSchema.TYPE)) {
                    urlKey = nextCloudApi.generateUrlDownload(filePath, fileName);
                }
                var expiryTime = OffsetDateTime.now().plusHours(1);
                var urlToken = new NextCloudToken(urlKey, true, expiryTime.toInstant().toEpochMilli());

                Request request;

                request = createRequest(resourceDefinition, urlToken, policy);
                try (var response = httpClient.execute(request)) {

                    if (response.isSuccessful()) {
                        return CompletableFuture.completedFuture(StatusResult.success(ProvisionResponse.Builder.newInstance().inProcess(true).build()));
                    } else if (response.code() >= 500 && response.code() <= 504) {
                        // retry
                        return CompletableFuture.completedFuture(StatusResult.failure(ResponseStatus.ERROR_RETRY, "HttpProviderProvisioner: received error code: " + response.code()));
                    } else {
                        // fatal error
                        return CompletableFuture.completedFuture(StatusResult.failure(ResponseStatus.FATAL_ERROR, "HttpProviderProvisioner: received fatal error code: " + response.code()));
                    }
                }


            } catch (Exception e) {
                monitor.severe("Error provisioning", e);
                return CompletableFuture.completedFuture(StatusResult.failure(ResponseStatus.FATAL_ERROR, e.getMessage()));
            }
        } else {
            var resourceBuilder = NextCloudProvisionedResource.Builder.newInstance()
                    .id(resourceDefinition.getId())
                    .resourceName(resourceName)
                    .filePath(filePath)
                    .fileName(fileName)
                    .urlKey(filePath + fileName + resourceDefinition.getId())
                    .resourceDefinitionId(resourceDefinition.getId())
                    .transferProcessId(resourceDefinition.getTransferProcessId())

                    .hasToken(true);

            var resource = resourceBuilder.build();
            var expiryTime = OffsetDateTime.now().plusHours(1);
            var urlToken = new NextCloudToken("", false, expiryTime.toInstant().toEpochMilli());

            var response = ProvisionResponse.Builder.newInstance().resource(resource).inProcess(true).secretToken((SecretToken) urlToken).build();
            try {
                nextCloudApi.fileShare(filePath,
                        fileName,
                        getProperties(policy,EDC_NAMESPACE+"shareWith"),
                        getProperties(policy,EDC_NAMESPACE+"shareType"),
                        getProperties(policy,EDC_NAMESPACE+"permissionType"),
                        nowDate(Integer.parseInt(getProperties(policy,EDC_NAMESPACE+"expirationTime"))));
            } catch (Exception e) {
                monitor.severe("Error sharing file, cause: ", e);
                return CompletableFuture.completedFuture(StatusResult.failure(ResponseStatus.FATAL_ERROR, e.getMessage()));
            }

            return CompletableFuture.completedFuture(StatusResult.success(response));
        }
    }

    @Override
    public CompletableFuture<StatusResult<DeprovisionedResource>> deprovision(NextCloudProvisionedResource provisionedResource, Policy policy) {
        return CompletableFuture.completedFuture(StatusResult.success(DeprovisionedResource.Builder.newInstance().provisionedResourceId(provisionedResource.getId()).build()));
    }

    private Request createRequest(NextCloudResourceDefinition resourceDefinition, NextCloudToken url, Policy policy) throws JsonProcessingException {
        var provisionerRequest = HttpParts.Builder.newInstance()
                .dataAddress(resourceDefinition.getDataAddress())
                .dataRequest(resourceDefinition.getDataRequest().getDataDestination())
                .assetId(resourceDefinition.getDataRequest().getAssetId())
                .transferProcessId(resourceDefinition.getTransferProcessId())
                .processId(resourceDefinition.getDataRequest().getId())
                .resourceDefinitionId(resourceDefinition.getId())
                .policy(policy)
                .url(url)
                .build();
        var requestBody = RequestBody.create(mapper.writeValueAsString(provisionerRequest), JSON);


        return new Request.Builder()
                .addHeader("X-API-Key", "%s".formatted(authKey))
                .url(resourceDefinition
                        .getDataRequest()
                        .getDataDestination()
                        .getStringProperty(NextcloudSchema.HTTP_RECEIVER) + endpoint)
                .post(requestBody).build();
    }




    private String nowDate(int plusDays) {
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime daysLater = now.plusDays(plusDays);
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        String formattedDate = daysLater.format(formatter);

        return formattedDate;
    }

    private String getProperties(Policy policy, String tag ){
        LinkedHashMap   policyMap = (LinkedHashMap) policy.getExtensibleProperties().values().stream().toList().get(0);

        ArrayList<Object> firstArrayList = (ArrayList<Object> ) policyMap.get(tag);

        // Access the first LinkedHashMap in the ArrayList
        LinkedHashMap<String, Object> firstLinkedHashMap = (LinkedHashMap<String, Object>) firstArrayList.get(0);

        // Get the value of the "@value" key
        Object value = firstLinkedHashMap.get("@value");
        return value.toString();
    }
}
