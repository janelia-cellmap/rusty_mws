from tqdm import tqdm
import numpy as np
import daisy
from skimage.morphology import ball, erosion, dilation
import logging
from funlib.persistence import Array, open_ds, prepare_ds

logger: logging.Logger = logging.getLogger(__name__)


def skel_correct_segmentation(
    raster_file="../../data/xpress-challenge.zarr",
    raster_name="volumes/validation_gt_rasters",
    frag_file="./raw_predictions.zarr",
    frag_name="frags",
    seg_file="./raw_predictions.zarr",
    seg_name="pred_seg",
    num_workers=25,
    # erode_iterations=1,
    erode_iterations=0,
    erode_footprint=ball(radius=5),
    alternate_dilate=True,
    dilate_footprint=ball(radius=5),
    n_chunk_write: int = 2,
) -> bool:
    frags: Array = open_ds(filename=frag_file, ds_name=frag_name)
    raster_ds: Array = open_ds(raster_file, raster_name)
    chunk_shape: tuple = frags.chunk_shape[frags.n_channel_dims :]

    # task params
    voxel_size = frags.voxel_size
    read_roi_voxels = daisy.Roi(
        (0, 0, 0), chunk_shape * n_chunk_write
    )  # TODO: may want to add context here
    write_roi_voxels = daisy.Roi((0, 0, 0), chunk_shape * n_chunk_write)
    total_roi = frags.roi
    dtype = frags.dtype
    read_roi = read_roi_voxels * voxel_size
    write_roi = write_roi_voxels * voxel_size

    # setup output zarr
    seg_ds = prepare_ds(
        filename=seg_file,
        ds_name=seg_name,
        total_roi=total_roi,
        voxel_size=voxel_size,
        dtype=dtype,
        delete=True,
    )

    # setup labels_mask zarr
    ds = prepare_ds(
        seg_file,
        "pred_labels_mask",
        total_roi=total_roi,
        voxel_size=voxel_size,
        dtype=np.uint8,
        delete=True,
    )

    # setup unlabelled_mask zarr
    ds = prepare_ds(
        seg_file,
        ds_name="pred_unlabelled_mask",
        total_roi=total_roi,
        voxel_size=voxel_size,
        dtype=np.uint8,
        delete=True,
    )

    seg_ds: Array = open_ds(filename=seg_file, ds_name=seg_name, mode="r+")

    def skel_correct_worker(
        block: daisy.Block, seg_ds=seg_ds, raster_ds=raster_ds
    ) -> bool:
        raster_array: np.ndarray = raster_ds.to_ndarray(block.read_roi)
        frag_array: np.ndarray = frags.to_ndarray(block.read_roi)
        assert raster_array.shape == frag_array.shape

        seg_array: np.ndarray = np.zeros_like(frag_array)

        for frag_id in tqdm(np.unique(frag_array)):
            if frag_id == 0:
                continue
            seg_ids: list = list(np.unique(raster_array[frag_array == frag_id]))

            if seg_ids[0] == 0:
                seg_ids.pop(0)
            if len(seg_ids) == 1:
                seg_array[frag_array == frag_id] = seg_ids[0]

        if erode_iterations > 0:
            for _ in range(erode_iterations):
                seg_array = erosion(seg_array, erode_footprint)
                if alternate_dilate:
                    seg_array = dilation(seg_array, dilate_footprint)

        logger.info("writing segmentation to disk")

        seg_ds[block.write_roi] = seg_array

        # Now make labels mask
        labels_mask = np.ones_like(seg_array).astype(np.uint8)
        labels_mask_ds = open_ds(seg_file, "pred_labels_mask", mode="a")
        labels_mask_ds[block.write_roi] = labels_mask

        # Now make the unlabelled mask
        unlabelled_mask = (seg_array > 0).astype(np.uint8)
        unlabelled_mask_ds = open_ds(seg_file, "pred_unlabelled_mask", mode="a")
        unlabelled_mask_ds[block.write_roi] = unlabelled_mask
        return True

    # create task
    task = daisy.Task(
        task_id="UpdateSegTask",
        total_roi=total_roi,
        read_roi=read_roi,
        write_roi=write_roi,
        process_function=skel_correct_worker,
        num_workers=num_workers,
    )

    # run task
    ret: bool = daisy.run_blockwise([task])
    return ret


if __name__ == "__main__":
    skel_correct_segmentation(
        raster_file="../../../data/xpress-challenge.zarr",
        raster_name="volumes/validation_gt_rasters",
        frag_file="./raw_predictions.zarr",
        frag_name="cropped_frags",
        seg_file="./raw_predictions.zarr",
    )
