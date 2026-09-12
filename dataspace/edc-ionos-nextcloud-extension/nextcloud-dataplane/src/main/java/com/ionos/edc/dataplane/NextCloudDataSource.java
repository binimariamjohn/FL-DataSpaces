package com.ionos.edc.dataplane;

import com.ionos.edc.nextcloudapi.NextCloudApi;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSource;
import org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.util.stream.Stream;
import static org.eclipse.edc.connector.dataplane.spi.pipeline.StreamResult.success;

public class NextCloudDataSource implements DataSource {
    private String fileName;
    private String filePath;
    private String url;
    private Boolean downloadable;
    private NextCloudApi nextCloudApi;

    @Override
    public StreamResult<Stream<Part>> openPartStream() {

            return success(Stream.of(new nextCloudPart(nextCloudApi, fileName, filePath, url, downloadable)));

    }

    @Override
    public void close() throws Exception {

    }

    private static class nextCloudPart  implements Part {
        private final NextCloudApi nextCloudApi;
        private String fileName;
        private String filePath;
        private String url;
        private Boolean downloadable;

        public nextCloudPart(NextCloudApi nextCloudApi, String fileName, String filePath, String url, Boolean downloadable) {
            this.nextCloudApi = nextCloudApi;
            this.fileName = fileName;
            this.filePath = filePath;
            this.url = url;
            this.downloadable = downloadable;
        }

        @Override
        public String name() {
            return fileName;
        }

        @Override
        public InputStream openStream() {
            if(downloadable) {
                return new ByteArrayInputStream(nextCloudApi.downloadFile(url));
            }else {
                return new ByteArrayInputStream("".getBytes());
            }
        }
    }
    public static class Builder {
        private final NextCloudDataSource source;
        public Builder fileName;

        private Builder() {
            source = new NextCloudDataSource();
        }

        public static Builder newInstance() {
            return new Builder();
        }

        public Builder fileName(String fileName) {
            source.fileName = fileName;
            return this;
        }

        public Builder filePath(String filePath) {
            source.filePath = filePath;
            return this;
        }

        public Builder url(String url) {
            source.url = url;
            return this;
        }

        public Builder downloadable(Boolean downloadable) {
            source.downloadable = downloadable;
            return this;
        }

        public Builder client(NextCloudApi nextCloudApi) {
            source.nextCloudApi = nextCloudApi;
            return this;
        }

        public NextCloudDataSource build() {
            return source;
        }
    }


}