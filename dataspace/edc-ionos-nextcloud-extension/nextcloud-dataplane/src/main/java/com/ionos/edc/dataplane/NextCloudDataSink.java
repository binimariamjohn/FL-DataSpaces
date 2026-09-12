package com.ionos.edc.dataplane;

import com.ionos.edc.nextcloudapi.NextCloudApi;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult;
import org.eclipse.edc.connector.dataplane.util.sink.ParallelSink;
import org.jetbrains.annotations.NotNull;
import java.io.ByteArrayInputStream;
import java.util.List;
import static java.lang.String.format;

public class NextCloudDataSink extends ParallelSink {
    private NextCloudApi nextCloudApi;
    private String filePath;
    private String fileName;
    private Boolean downloadable;

    public NextCloudDataSink() {
    }

    @Override
    protected StreamResult<Object> transferParts(List<DataSource.Part> parts) {

        if(downloadable) {
            for (var part : parts) {
                try (var input = part.openStream()) {

                    nextCloudApi.uploadFile(filePath, fileName, new ByteArrayInputStream(input.readAllBytes()));
                    //nextCloudApi.uploadFile(filePath, fileName, input);
                } catch (Exception e) {
                    return uploadFailure(e, fileName);
                }
            }
        }
        return StreamResult.success(new ByteArrayInputStream("".getBytes()));
    }

    @NotNull
    private StreamResult<Object> uploadFailure(Exception e, String fileName) {
        var message = format("Error writing the %s object on the nextcloud", fileName, e.getMessage());
        monitor.severe(message, e);
        return StreamResult.error(message);
    }


    public static class Builder extends ParallelSink.Builder<Builder, NextCloudDataSink> {
        private Builder() {
            super(new NextCloudDataSink());
        }

        public static Builder newInstance() {
            return new Builder();
        }

        public Builder nextCloudApi(NextCloudApi nextCloudApi) {
            sink.nextCloudApi = nextCloudApi;
            return this;
        }

        public Builder filePath(String filePath) {
            sink.filePath = filePath;
            return this;
        }

        public Builder fileName(String fileName) {
            sink.fileName = fileName;
            return this;
        }
        
        public Builder downloadable(Boolean downloadable) {
            sink.downloadable = downloadable;
            return this;
        }

        @Override
        protected void validate() {}
    }
}